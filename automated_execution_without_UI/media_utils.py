import io
import os
import subprocess
import tempfile
import time

import requests
from PIL import Image

from config import MEDIA_DOWNLOAD_TIMEOUT


def timed_call(func, *args, **kwargs):
    """Run func(*args, **kwargs) and return (result, elapsed_seconds, error_string_or_None)."""
    start = time.time()
    try:
        result = func(*args, **kwargs)
        return result, time.time() - start, None
    except Exception as exc:
        return None, time.time() - start, str(exc)


def download_media(url, timeout=MEDIA_DOWNLOAD_TIMEOUT):
    """Download media from URL and return raw bytes."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def normalize_image_bytes(image_bytes):
    """Convert image bytes to a Bedrock-compatible format (JPEG/PNG).

    Returns (normalized_bytes, format_string) where format_string is 'jpeg' or 'png'.
    WebP and other formats are converted to JPEG.
    """
    img = Image.open(io.BytesIO(image_bytes))
    fmt = (img.format or "").upper()

    if fmt in ("JPEG", "JPG"):
        return image_bytes, "jpeg"
    if fmt == "PNG":
        return image_bytes, "png"

    # Convert everything else (WebP, BMP, TIFF, etc.) to JPEG
    buf = io.BytesIO()
    rgb_img = img.convert("RGB") if img.mode != "RGB" else img
    rgb_img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "jpeg"


def extract_video_frames(video_bytes, num_frames=5):
    """Extract evenly-spaced frames from video bytes using ffmpeg.

    Returns a list of (jpeg_bytes, 'jpeg') tuples.
    """
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "input.mp4")
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        # Get total frame count
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_packets", "-show_entries", "stream=nb_read_packets",
                "-of", "csv=p=0", video_path,
            ],
            capture_output=True, text=True,
        )
        total_frames = int(probe.stdout.strip()) if probe.stdout.strip() else 100
        step = max(1, total_frames // num_frames)

        output_pattern = os.path.join(tmp, "frame_%04d.jpg")
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vf", f"select='not(mod(n\\,{step}))',scale=640:-1",
                "-vsync", "vfr", "-q:v", "2",
                "-frames:v", str(num_frames),
                output_pattern,
            ],
            capture_output=True, check=True,
        )

        frames = []
        for i in range(1, num_frames + 1):
            fp = os.path.join(tmp, f"frame_{i:04d}.jpg")
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    frames.append((f.read(), "jpeg"))

    return frames
