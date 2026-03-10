#!/usr/bin/env python3
"""Batch LLM content moderation — CLI entry point.

Reads test cases from an xlsx file and runs moderation via AWS Bedrock.
"""

import argparse
import logging
import os
import sys

import openpyxl

# Ensure the local package directory is first in sys.path
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

from config import DEFAULT_MODEL_ID, DEFAULT_LANG, MODEL_LIST  # noqa: E402
from llm_moderator import moderate_text, moderate_image, moderate_video  # noqa: E402
from output_formatter import save_results_json, save_summary_txt, save_results_xlsx  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# XLSX loader
# ---------------------------------------------------------------------------

def load_test_sets(excel_path):
    """Load text, image URLs, and video URLs from the xlsx file.

    Returns (texts, image_urls, video_urls) — each a list of (row_index, value).
    """
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    texts = []
    image_urls = []
    video_urls = []

    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
        text_val = row[0] if len(row) > 0 else None
        image_val = row[1] if len(row) > 1 else None
        video_val = row[2] if len(row) > 2 else None

        if text_val and str(text_val).strip():
            texts.append((idx, str(text_val).strip()))
        if image_val and str(image_val).strip():
            image_urls.append((idx, str(image_val).strip()))
        if video_val and str(video_val).strip():
            video_urls.append((idx, str(video_val).strip()))

    wb.close()
    return texts, image_urls, video_urls


# ---------------------------------------------------------------------------
# Moderation runners
# ---------------------------------------------------------------------------

def run_text_moderation(texts, model_id, lang):
    results = []
    total = len(texts)
    for i, (row_idx, text) in enumerate(texts):
        logger.info("[Text %d/%d] Row %d  (%d chars)", i + 1, total, row_idx, len(text))
        result = moderate_text(row_idx, text, model_id, lang=lang)
        risk = result.moderation.overall_risk if result.moderation else "ERROR"
        logger.info("  -> %s  (%.1fs)", risk, result.moderation_time_sec)
        results.append(result)
    return results


def run_image_moderation(image_urls, model_id, lang):
    results = []
    total = len(image_urls)
    for i, (row_idx, url) in enumerate(image_urls):
        logger.info("[Image %d/%d] Row %d  %s", i + 1, total, row_idx, url[:80])
        result = moderate_image(row_idx, url, model_id, lang=lang)
        if result.error:
            logger.warning("  -> ERROR: %s", result.error[:80])
        else:
            risk = result.moderation.overall_risk if result.moderation else "parse_err"
            logger.info("  -> %s  (dl=%.1fs mod=%.1fs)", risk, result.download_time_sec, result.moderation_time_sec)
        results.append(result)
    return results


def run_video_moderation(video_urls, model_id, lang, num_frames):
    results = []
    total = len(video_urls)
    for i, (row_idx, url) in enumerate(video_urls):
        logger.info("[Video %d/%d] Row %d  %s", i + 1, total, row_idx, url[:80])
        result = moderate_video(row_idx, url, model_id, lang=lang, num_frames=num_frames)
        if result.error:
            logger.warning("  -> ERROR: %s", result.error[:80])
        else:
            risk = result.moderation.overall_risk if result.moderation else "parse_err"
            logger.info(
                "  -> %s  [%s] (dl=%.1fs mod=%.1fs)",
                risk, result.analysis_method, result.download_time_sec, result.moderation_time_sec,
            )
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch LLM content moderation via AWS Bedrock",
    )
    parser.add_argument(
        "-m", "--model", default=DEFAULT_MODEL_ID,
        help=f"Model ID for text/image moderation (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--video-model", default=None,
        help="Override model for video moderation (defaults to --model)",
    )
    parser.add_argument(
        "-e", "--excel", default=os.path.join(os.path.dirname(__file__), "test-sets.xlsx"),
        help="Path to test-sets.xlsx",
    )
    parser.add_argument(
        "-o", "--output-dir", default=os.path.dirname(__file__) or ".",
        help="Output directory for results.json and summary.txt",
    )
    parser.add_argument("--text-only", action="store_true", help="Run text moderation only")
    parser.add_argument("--image-only", action="store_true", help="Run image moderation only")
    parser.add_argument("--video-only", action="store_true", help="Run video moderation only")
    parser.add_argument(
        "--num-frames", type=int, default=5,
        help="Number of frames for frame-based video analysis (default: 5)",
    )
    parser.add_argument(
        "--lang", default=DEFAULT_LANG, choices=["zh", "en"],
        help=f"Output language for LLM responses: zh=Chinese, en=English (default: {DEFAULT_LANG})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Load xlsx and print counts, no API calls")
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate model
    if args.model not in MODEL_LIST:
        logger.error("Unknown model: %s", args.model)
        logger.info("Available models: %s", ", ".join(MODEL_LIST))
        sys.exit(1)

    video_model = args.video_model or args.model
    if video_model not in MODEL_LIST:
        logger.error("Unknown video model: %s", video_model)
        sys.exit(1)

    # Determine which content types to run
    run_all = not (args.text_only or args.image_only or args.video_only)
    do_text = run_all or args.text_only
    do_image = run_all or args.image_only
    do_video = run_all or args.video_only

    # Load xlsx
    logger.info("Loading test sets from %s", args.excel)
    texts, image_urls, video_urls = load_test_sets(args.excel)
    logger.info("Found: %d texts, %d images, %d videos", len(texts), len(image_urls), len(video_urls))

    if args.dry_run:
        logger.info("Dry run complete. Model: %s / Video model: %s / Lang: %s", args.model, video_model, args.lang)
        for i, (idx, t) in enumerate(texts[:3]):
            logger.info("  Text sample %d (row %d): %s...", i, idx, t[:80])
        for i, (idx, u) in enumerate(image_urls[:3]):
            logger.info("  Image sample %d (row %d): %s", i, idx, u)
        for i, (idx, u) in enumerate(video_urls[:3]):
            logger.info("  Video sample %d (row %d): %s", i, idx, u)
        return

    os.makedirs(args.output_dir, exist_ok=True)

    text_results = []
    image_results = []
    video_results = []

    # Run moderation
    if do_text and texts:
        logger.info("=== Text Moderation (%d rows, model=%s) ===", len(texts), args.model)
        text_results = run_text_moderation(texts, args.model, args.lang)

    if do_image and image_urls:
        logger.info("=== Image Moderation (%d rows, model=%s) ===", len(image_urls), args.model)
        image_results = run_image_moderation(image_urls, args.model, args.lang)

    if do_video and video_urls:
        logger.info("=== Video Moderation (%d rows, model=%s) ===", len(video_urls), video_model)
        video_results = run_video_moderation(video_urls, video_model, args.lang, args.num_frames)

    # Save results
    effective_model = args.model
    json_path = save_results_json(text_results, image_results, video_results, effective_model, args.output_dir)
    txt_path = save_summary_txt(text_results, image_results, video_results, effective_model, args.output_dir)
    xlsx_path = save_results_xlsx(text_results, image_results, video_results, effective_model, args.output_dir)

    logger.info("Results saved: %s", json_path)
    logger.info("Summary saved: %s", txt_path)
    logger.info("Excel saved:   %s", xlsx_path)

    # Print quick stats
    total = len(text_results) + len(image_results) + len(video_results)
    errors = sum(1 for r in text_results + image_results + video_results if r.error)
    logger.info("Done: %d total, %d success, %d errors", total, total - errors, errors)


if __name__ == "__main__":
    main()
