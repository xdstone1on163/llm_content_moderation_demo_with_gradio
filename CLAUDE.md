# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multimedia content moderation demo using AWS AI services and Gradio. It provides five moderation tabs: Image, Static Video, Video Stream (webcam), Audio/Video Transcription, and Text. Each tab combines LLM analysis (via AWS Bedrock) with purpose-built AWS services (Rekognition, Comprehend, Transcribe).

## Running the Application

```bash
# Setup (conda recommended)
conda create -n myenv python=3.11 && conda activate myenv
pip install -r requirements.txt

# System dependency: ffmpeg must be installed (brew install ffmpeg)

# Run
python main.py
```

The app launches a Gradio web UI with `share=True` (public URL).

## AWS Configuration

- Requires configured AWS credentials (`aws configure`) with us-west-2 region
- `.env` file at project root for `S3_BUCKET_NAME` and optional overrides (`S3_REGION`, `TRANSCRIBE_BUCKET`)
- Required AWS services: Bedrock (Claude + Nova models), Rekognition, Comprehend, Transcribe, S3
- Bedrock models must be enabled in the AWS console before use

## Architecture

**Entry point:** `main.py` — builds the entire Gradio UI with tabbed layout. Left sidebar has model selector; right side has five tabs. Uses `gr.Blocks` with threading for real-time video stream analysis.

**Modular audit files** — each handles one content type:
- `image_audit.py` — LLM (Bedrock Converse API) + Rekognition (moderation labels, detection labels, face detection)
- `video_audit.py` — Two modes: frame-based (ffmpeg extracts frames → LLM analyzes) and direct understanding (Nova models process video bytes or S3 URIs natively)
- `text_audit.py` — LLM analysis + Comprehend (sentiment, entities, key phrases, PII, toxicity)
- `audio_audit.py` — Uploads audio to S3 → AWS Transcribe job → polls for results with toxicity detection (English only). Creates its own Gradio sub-interface via `create_audio_interface()`
- `video_stream.py` — Frame storage utilities for webcam streaming. Gradio's native `gr.Image(streaming=True)` handles camera access via the browser; this module provides `process_streaming_frame()` (rate-limited frame saving), `get_captured_frames()`, and `clear_captured_frames()`. No OpenCV or threading dependencies

**Shared modules:**
- `aws_clients.py` — Singleton boto3 clients for all AWS services. Key functions: `converse_with_model()` (Bedrock Converse API wrapper used by image/video/text), `invoke_model()` (raw Bedrock invoke used by Nova video), `start_transcription_job()`
- `config.py` — Loads `.env` via python-dotenv. Contains all default prompts, model IDs, model price list, and S3 config
- `utils.py` — `encode_image()` (base64) and `get_image_bytes()` for PIL/numpy/path → bytes conversion

**`single_file_to_run/`** — Self-contained earlier versions of the app (v1, v2, current) that bundle everything in one file. These are standalone demos, not used by the main app.

## Key Patterns

- **Bedrock Converse API** is the primary LLM interface (not direct invoke), except for Nova video which uses `invoke_model()` with a native JSON request body
- **Nova models** (`us.amazon.nova-lite-v1:0`, `us.amazon.nova-pro-v1:0`) are the only models supporting direct video understanding; Claude models are used for frame-based analysis
- Video frame-based analysis uses **ffmpeg/ffprobe** subprocess calls to extract frames and count packets
- Audio transcription is async: upload WAV to S3 → start Transcribe job → poll `get_transcription_job()` every 5s with 5min timeout
- Video stream uses Gradio native webcam streaming (`gr.Image(streaming=True)`) — browser handles camera access, Python backend saves frames when capturing is toggled on. Analysis still runs in a daemon thread with `log_queue` for status updates
- All prompts are configurable through the Gradio UI, with defaults in `config.py`
- The moderation flag system in `DEFAULT_IMAGE_PROMPT` uses numeric severity levels: 999 (most severe) → 0 (no violation)
