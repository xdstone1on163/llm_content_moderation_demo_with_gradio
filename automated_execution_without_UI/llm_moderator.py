import importlib.util
import json
import logging
import os
import re
import time

# Import converse_with_model from parent project's aws_clients
_aws_path = os.path.join(os.path.dirname(__file__), "..", "aws_clients.py")
_spec = importlib.util.spec_from_file_location("parent_aws_clients", _aws_path)
_aws_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_aws_mod)
converse_with_model = _aws_mod.converse_with_model
bedrock_client = _aws_mod.bedrock_client

from config import (
    DEFAULT_LANG,
    DIRECT_VIDEO_MODELS,
    INVOKE_MODEL_IMAGE_MODELS,
    TEXT_ONLY_MODELS,
    get_prompts,
)
from models import (
    ModerationCategory,
    ModerationResult,
    TextModerationResult,
    ImageModerationResult,
    VideoModerationResult,
)
from media_utils import (
    timed_call,
    download_media,
    normalize_image_bytes,
    extract_video_frames,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_moderation_response(raw_text):
    """Extract ModerationResult from LLM response text.

    Handles JSON inside ```json ... ``` blocks, raw JSON, or JSON with surrounding prose.
    Returns ModerationResult or None on failure.
    """
    # Try code-block extraction first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    text = match.group(1) if match else raw_text

    # Try to find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None

    cats = data.get("categories", {})
    if not cats:
        return None

    def _cat(name):
        c = cats.get(name, {})
        return ModerationCategory(
            detected=bool(c.get("detected", False)),
            severity=str(c.get("severity", "none")),
            details=str(c.get("details", "")),
        )

    return ModerationResult(
        pornography=_cat("pornography"),
        violence=_cat("violence"),
        tobacco_alcohol=_cat("tobacco_alcohol"),
        political_sensitivity=_cat("political_sensitivity"),
        profanity=_cat("profanity"),
        overall_risk=str(data.get("overall_risk", "unknown")),
        summary=str(data.get("summary", "")),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _supports_direct_video(model_id):
    return model_id in DIRECT_VIDEO_MODELS


def _is_text_only(model_id):
    return model_id in TEXT_ONLY_MODELS


def _uses_invoke_model_for_images(model_id):
    return model_id in INVOKE_MODEL_IMAGE_MODELS


_LLM_ERROR_PREFIXES = ("Model invocation error", "Model returned empty response")


def _call_llm(model_id, system_prompt, messages):
    """Call Bedrock Converse API and return (response_text, elapsed_sec).

    Raises RuntimeError if the upstream converse_with_model() returns an error string.
    """
    start = time.time()
    result = converse_with_model(
        model_id=model_id,
        system_prompts=[{"text": system_prompt}],
        messages=messages,
        max_tokens=2000,
        temperature=0.1,
    )
    elapsed = time.time() - start
    if isinstance(result, str) and result.startswith(_LLM_ERROR_PREFIXES):
        raise RuntimeError(result)
    return result, elapsed


import base64

_MIME_TYPES = {"jpeg": "image/jpeg", "jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}


def _call_invoke_model(model_id, system_prompt, prompt_text, image_bytes_list=None):
    """Call Bedrock invoke_model with OpenAI-compatible format (for models that don't support Converse image field).

    image_bytes_list: list of (bytes, format_str) tuples, or None for text-only.
    Returns (response_text, elapsed_sec). Raises RuntimeError on failure.
    """
    content_parts = []

    # System prompt as first text
    if system_prompt:
        content_parts.append({"type": "text", "text": system_prompt})

    # Images
    if image_bytes_list:
        for img_bytes, fmt in image_bytes_list:
            mime = _MIME_TYPES.get(fmt, "image/jpeg")
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })

    # User prompt text
    content_parts.append({"type": "text", "text": prompt_text})

    body = json.dumps({
        "messages": [{"role": "user", "content": content_parts}],
        "max_tokens": 2000,
        "temperature": 0.1,
    })

    start = time.time()
    resp = bedrock_client.invoke_model(
        body=body,
        contentType="application/json",
        accept="application/json",
        modelId=model_id,
    )
    elapsed = time.time() - start

    result_body = json.loads(resp["body"].read())
    choices = result_body.get("choices", [])
    if not choices:
        raise RuntimeError("invoke_model returned no choices")
    text = choices[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError("invoke_model returned empty content")
    return text, elapsed


# ---------------------------------------------------------------------------
# Text moderation
# ---------------------------------------------------------------------------

def moderate_text(row_index, text, model_id, lang=DEFAULT_LANG, prompt=None, system_prompt=None):
    sys_p, text_p, _, _ = get_prompts(lang)
    prompt = prompt or text_p
    system_prompt = system_prompt or sys_p

    messages = [{"role": "user", "content": [{"text": prompt + text}]}]

    try:
        raw, elapsed = _call_llm(model_id, system_prompt, messages)
        moderation = _parse_moderation_response(raw)
        return TextModerationResult(
            row_index=row_index,
            original_text=text,
            model_id=model_id,
            moderation_time_sec=round(elapsed, 3),
            moderation=moderation,
            raw_llm_response=raw,
            error=None,
        )
    except Exception as exc:
        logger.error("Text moderation error row %d: %s", row_index, exc)
        return TextModerationResult(
            row_index=row_index,
            original_text=text,
            model_id=model_id,
            moderation_time_sec=0.0,
            moderation=None,
            raw_llm_response="",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Image moderation
# ---------------------------------------------------------------------------

def moderate_image(row_index, image_url, model_id, lang=DEFAULT_LANG, prompt=None, system_prompt=None):
    if _is_text_only(model_id):
        return ImageModerationResult(
            row_index=row_index, image_url=image_url, model_id=model_id,
            download_time_sec=0.0, moderation_time_sec=0.0,
            image_size_bytes=0, moderation=None, raw_llm_response="",
            error=f"Model {model_id} is text-only, cannot process images",
        )
    sys_p, _, img_p, _ = get_prompts(lang)
    prompt = prompt or img_p
    system_prompt = system_prompt or sys_p

    # Download
    image_bytes, dl_time, dl_error = timed_call(download_media, image_url)
    if dl_error:
        return ImageModerationResult(
            row_index=row_index, image_url=image_url, model_id=model_id,
            download_time_sec=round(dl_time, 3), moderation_time_sec=0.0,
            image_size_bytes=0, moderation=None, raw_llm_response="",
            error=f"Download failed: {dl_error}",
        )

    # Normalize image format
    try:
        norm_bytes, img_fmt = normalize_image_bytes(image_bytes)
    except Exception as exc:
        return ImageModerationResult(
            row_index=row_index, image_url=image_url, model_id=model_id,
            download_time_sec=round(dl_time, 3), moderation_time_sec=0.0,
            image_size_bytes=len(image_bytes), moderation=None, raw_llm_response="",
            error=f"Image conversion failed: {exc}",
        )

    # Call LLM — route by model type
    try:
        if _uses_invoke_model_for_images(model_id):
            raw, elapsed = _call_invoke_model(
                model_id, system_prompt, prompt,
                image_bytes_list=[(norm_bytes, img_fmt)],
            )
        else:
            content = [
                {"image": {"format": img_fmt, "source": {"bytes": norm_bytes}}},
                {"text": prompt},
            ]
            messages = [{"role": "user", "content": content}]
            raw, elapsed = _call_llm(model_id, system_prompt, messages)
        moderation = _parse_moderation_response(raw)
        return ImageModerationResult(
            row_index=row_index, image_url=image_url, model_id=model_id,
            download_time_sec=round(dl_time, 3), moderation_time_sec=round(elapsed, 3),
            image_size_bytes=len(image_bytes), moderation=moderation,
            raw_llm_response=raw, error=None,
        )
    except Exception as exc:
        logger.error("Image moderation error row %d: %s", row_index, exc)
        return ImageModerationResult(
            row_index=row_index, image_url=image_url, model_id=model_id,
            download_time_sec=round(dl_time, 3), moderation_time_sec=0.0,
            image_size_bytes=len(image_bytes), moderation=None,
            raw_llm_response="", error=str(exc),
        )


# ---------------------------------------------------------------------------
# Video moderation
# ---------------------------------------------------------------------------

def moderate_video(row_index, video_url, model_id, lang=DEFAULT_LANG, prompt=None, system_prompt=None, num_frames=5):
    if _is_text_only(model_id):
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method="unsupported", download_time_sec=0.0,
            moderation_time_sec=0.0, video_size_bytes=0, moderation=None,
            raw_llm_response="",
            error=f"Model {model_id} is text-only, cannot process video",
        )

    sys_p, _, _, vid_p = get_prompts(lang)
    prompt = prompt or vid_p
    system_prompt = system_prompt or sys_p

    # Download
    video_bytes, dl_time, dl_error = timed_call(download_media, video_url)
    if dl_error:
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method="unknown", download_time_sec=round(dl_time, 3),
            moderation_time_sec=0.0, video_size_bytes=0, moderation=None,
            raw_llm_response="", error=f"Download failed: {dl_error}",
        )

    use_direct = _supports_direct_video(model_id)

    if use_direct:
        result = _moderate_video_direct(
            row_index, video_url, video_bytes, model_id, prompt, system_prompt, dl_time, "direct",
        )
        if result.error:
            logger.warning("  Direct mode failed for row %d, falling back to frame-based: %s",
                           row_index, result.error[:80])
            return _moderate_video_frames(
                row_index, video_url, video_bytes, model_id, prompt, system_prompt, dl_time,
                "frame_based(fallback)", num_frames,
            )
        return result

    return _moderate_video_frames(
        row_index, video_url, video_bytes, model_id, prompt, system_prompt, dl_time, "frame_based", num_frames,
    )


def _moderate_video_direct(row_index, video_url, video_bytes, model_id, prompt, system_prompt, dl_time, method):
    """Send video bytes directly to a Nova model via Converse API."""
    content = [
        {"video": {"format": "mp4", "source": {"bytes": video_bytes}}},
        {"text": prompt},
    ]
    messages = [{"role": "user", "content": content}]

    try:
        raw, elapsed = _call_llm(model_id, system_prompt, messages)
        moderation = _parse_moderation_response(raw)
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=round(elapsed, 3), video_size_bytes=len(video_bytes),
            moderation=moderation, raw_llm_response=raw, error=None,
        )
    except Exception as exc:
        logger.error("Video direct moderation error row %d: %s", row_index, exc)
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=0.0, video_size_bytes=len(video_bytes),
            moderation=None, raw_llm_response="", error=str(exc),
        )


def _moderate_video_frames(row_index, video_url, video_bytes, model_id, prompt, system_prompt, dl_time, method, num_frames):
    """Extract frames via ffmpeg and send as multi-image to Claude."""
    try:
        frames = extract_video_frames(video_bytes, num_frames)
    except Exception as exc:
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=0.0, video_size_bytes=len(video_bytes),
            moderation=None, raw_llm_response="",
            error=f"Frame extraction failed: {exc}",
        )

    if not frames:
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=0.0, video_size_bytes=len(video_bytes),
            moderation=None, raw_llm_response="",
            error="No frames extracted from video",
        )

    try:
        if _uses_invoke_model_for_images(model_id):
            raw, elapsed = _call_invoke_model(
                model_id, system_prompt, prompt,
                image_bytes_list=frames,
            )
        else:
            content = [{"text": prompt}]
            for idx, (frame_bytes, fmt) in enumerate(frames):
                content.append({"image": {"format": fmt, "source": {"bytes": frame_bytes}}})
                content.append({"text": f"Frame {idx + 1} of {len(frames)}"})
            messages = [{"role": "user", "content": content}]
            raw, elapsed = _call_llm(model_id, system_prompt, messages)
        moderation = _parse_moderation_response(raw)
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=round(elapsed, 3), video_size_bytes=len(video_bytes),
            moderation=moderation, raw_llm_response=raw, error=None,
        )
    except Exception as exc:
        logger.error("Video frame moderation error row %d: %s", row_index, exc)
        return VideoModerationResult(
            row_index=row_index, video_url=video_url, model_id=model_id,
            analysis_method=method, download_time_sec=round(dl_time, 3),
            moderation_time_sec=0.0, video_size_bytes=len(video_bytes),
            moderation=None, raw_llm_response="", error=str(exc),
        )
