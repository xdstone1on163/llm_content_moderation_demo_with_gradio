import time
import uuid
import logging
import os

from aws_clients import rekognition_client, s3_client
from config import (
    S3_BUCKET_NAME,
    REKOGNITION_VIDEO_MIN_CONFIDENCE,
    REKOGNITION_POLL_INTERVAL,
    REKOGNITION_POLL_TIMEOUT,
)

logger = logging.getLogger(__name__)


def parse_s3_uri(s3_uri):
    """Parse s3://bucket/key into (bucket, key)."""
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    path = s3_uri[len("s3://"):]
    bucket, _, key = path.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return bucket, key


def upload_video_to_s3(video_path):
    """Upload a local video file to S3 and return (bucket, key)."""
    ext = os.path.splitext(video_path)[1] or ".mp4"
    key = f"video-moderation/{uuid.uuid4()}{ext}"
    s3_client.upload_file(video_path, S3_BUCKET_NAME, key)
    logger.info(f"Uploaded {video_path} to s3://{S3_BUCKET_NAME}/{key}")
    return S3_BUCKET_NAME, key


def start_video_moderation(bucket, key, min_confidence=None):
    """Start a Rekognition video content moderation job and return the job ID."""
    if min_confidence is None:
        min_confidence = REKOGNITION_VIDEO_MIN_CONFIDENCE
    response = rekognition_client.start_content_moderation(
        Video={"S3Object": {"Bucket": bucket, "Name": key}},
        MinConfidence=min_confidence,
    )
    job_id = response["JobId"]
    logger.info(f"Started Rekognition video moderation job: {job_id}")
    return job_id


def poll_video_moderation(job_id, poll_interval=None, timeout=None):
    """Poll get_content_moderation until complete, handling pagination. Returns full response dict."""
    if poll_interval is None:
        poll_interval = REKOGNITION_POLL_INTERVAL
    if timeout is None:
        timeout = REKOGNITION_POLL_TIMEOUT

    deadline = time.time() + timeout
    while time.time() < deadline:
        response = rekognition_client.get_content_moderation(
            JobId=job_id, SortBy="TIMESTAMP"
        )
        status = response["JobStatus"]
        if status == "SUCCEEDED":
            all_labels = list(response.get("ModerationLabels", []))
            next_token = response.get("NextToken")
            while next_token:
                page = rekognition_client.get_content_moderation(
                    JobId=job_id, SortBy="TIMESTAMP", NextToken=next_token
                )
                all_labels.extend(page.get("ModerationLabels", []))
                next_token = page.get("NextToken")
            return {"JobStatus": "SUCCEEDED", "ModerationLabels": all_labels}
        if status == "FAILED":
            reason = response.get("StatusMessage", "Unknown error")
            return {"JobStatus": "FAILED", "StatusMessage": reason}
        time.sleep(poll_interval)

    return {"JobStatus": "TIMED_OUT", "StatusMessage": "Polling timed out"}


def _format_timestamp(ms):
    """Convert milliseconds to MM:SS.mmm string."""
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def format_moderation_results(response):
    """Format Rekognition video moderation response into a readable string."""
    status = response.get("JobStatus", "UNKNOWN")

    if status == "FAILED":
        reason = response.get("StatusMessage", "Unknown error")
        return f"=== Rekognition Video Content Moderation ===\nStatus: FAILED\nReason: {reason}"

    if status == "TIMED_OUT":
        return "=== Rekognition Video Content Moderation ===\nStatus: TIMED_OUT\nThe moderation job did not complete within the timeout period."

    labels = response.get("ModerationLabels", [])
    if not labels:
        return "=== Rekognition Video Content Moderation ===\nStatus: SUCCEEDED\nNo moderation labels detected."

    categories = set()
    highest_conf = 0.0
    highest_label = ""
    highest_ts = 0

    lines = []
    for item in labels:
        ts = item.get("Timestamp", 0)
        label_info = item.get("ModerationLabel", {})
        name = label_info.get("Name", "Unknown")
        confidence = label_info.get("Confidence", 0.0)
        parent = label_info.get("ParentName", "")

        categories.add(parent if parent else name)

        suffix = f" -> {parent}" if parent else ""
        lines.append(f"[{_format_timestamp(ts)}] {name} ({confidence:.2f}%){suffix}")

        if confidence > highest_conf:
            highest_conf = confidence
            highest_label = name
            highest_ts = ts

    header = (
        f"=== Rekognition Video Content Moderation ===\n"
        f"Status: SUCCEEDED\n"
        f"Labels found: {len(labels)} | Categories: {', '.join(sorted(categories))}\n"
    )
    timeline = "\n--- Timeline ---\n" + "\n".join(lines)
    summary = (
        f"\n\n--- Summary ---\n"
        f"Highest: {highest_label} ({highest_conf:.2f}%) at {_format_timestamp(highest_ts)}"
    )
    return header + timeline + summary


def run_video_moderation(video_path, is_s3_path=False):
    """Orchestrate the full Rekognition video moderation flow. Returns formatted result string."""
    try:
        if is_s3_path:
            bucket, key = parse_s3_uri(video_path)
        else:
            bucket, key = upload_video_to_s3(video_path)

        job_id = start_video_moderation(bucket, key)
        response = poll_video_moderation(job_id)
        return format_moderation_results(response)
    except Exception as e:
        logger.error(f"Rekognition video moderation error: {e}")
        return f"=== Rekognition Video Content Moderation ===\nError: {e}"
