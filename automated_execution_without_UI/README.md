# Batch LLM Content Moderation (Headless CLI)

Automated batch content moderation tool that reads test cases from an Excel file and runs LLM-based analysis via AWS Bedrock — no UI required.

## Quick Start

```bash
# Activate your Python environment
source /path/to/venv/bin/activate

# Dry run — validate Excel loading and config without API calls
python main.py --dry-run

# Full run with default model (Claude Sonnet 4.6)
python main.py -e test-sets.xlsx

# Text moderation only
python main.py --text-only

# Use a specific model
python main.py -m us.amazon.nova-pro-v1:0

# English output (default is Chinese)
python main.py --lang en
```

## Excel Input Format

The input Excel file must have 3 columns in the first sheet:

| Column A (文本) | Column B (图片) | Column C (视频) |
|-----------------|----------------|----------------|
| Text to moderate | Image URL | Video URL |
| 待审核文本 | https://example.com/img.jpg | https://example.com/vid.mp4 |

- Row 1 is the header row (skipped)
- Each column is independent — empty cells are skipped
- A sample file `test-sets-sample.xlsx` is included as a template

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `-m`, `--model` | `global.anthropic.claude-sonnet-4-6` | Model ID for text/image moderation |
| `--video-model` | same as `--model` | Override model for video moderation |
| `-e`, `--excel` | `./test-sets.xlsx` | Path to input Excel file |
| `-o`, `--output-dir` | current directory | Output directory for results |
| `--lang` | `zh` | Output language: `zh` (Chinese) or `en` (English) |
| `--text-only` | | Run text moderation only |
| `--image-only` | | Run image moderation only |
| `--video-only` | | Run video moderation only |
| `--num-frames` | `5` | Number of frames for frame-based video analysis |
| `--dry-run` | | Validate config and Excel, no API calls |

## Moderation Categories

Each piece of content is analyzed across 5 categories:

| Category | Key | Description |
|----------|-----|-------------|
| Pornography | `pornography` | Nudity, sexual content, sexually suggestive material |
| Violence | `violence` | Physical harm, threats, gore, weapons |
| Tobacco/Alcohol | `tobacco_alcohol` | Smoking, drinking, drug use or promotion |
| Political Sensitivity | `political_sensitivity` | Chinese leaders, geopolitics (Taiwan/Tibet/HK/Xinjiang), CCP criticism, dictatorship/authoritarianism descriptions |
| Profanity | `profanity` | Swearing, insults, personal attacks, threatening language |

Each category returns:
- `detected`: boolean
- `severity`: `none` / `low` / `medium` / `high`
- `details`: description in the selected language (zh/en)

Overall risk level: `safe` / `low` / `medium` / `high` / `critical`

## Output Files

Each run produces 3 output files:

### `results.json`
Complete structured results with raw LLM responses, timing data, and parsed moderation results.

### `summary.txt`
Human-readable text tables showing per-row results, detected categories, and timing summary.

### `results.xlsx`
Excel workbook with 4 sheets:

| Sheet | Content |
|-------|---------|
| **Text Moderation** | Row, time, overall risk, 5 category severities + details, summary, original text |
| **Image Moderation** | Row, download/moderation time, size, risk, 5 categories, summary, URL |
| **Video Moderation** | Row, download/moderation time, method, size, risk, 5 categories, summary, URL |
| **Summary** | Run info, timing stats, detection rates per category, risk distribution |

Severity cells are color-coded: critical (dark red), high (red), medium (yellow), low (green). Error rows are highlighted in pink.

## Model Routing

The tool automatically routes API calls based on model capability:

```
Model selected
  ├── Text moderation → All models (Converse API)
  ├── Image moderation
  │     ├── Text-only model → Skip with error message
  │     ├── Converse API model (Claude, Qwen VL) → Converse API with image bytes
  │     └── InvokeModel model (Kimi K2.5) → InvokeModel with base64 image
  └── Video moderation
        ├── Text-only model → Skip with error message
        ├── Nova model → Direct video understanding
        │     └── If fails → Fallback to frame-based
        ├── Converse API model → ffmpeg frame extraction → multi-image Converse
        └── InvokeModel model → ffmpeg frame extraction → multi-image InvokeModel
```

## Supported Models

See the [pricing table in the main README](../README.md#supported-models-and-pricing) for the full list of 20+ supported models with pricing.

## Architecture

```
main.py              CLI entry point, xlsx loading, orchestration
config.py            Prompts (zh/en), model capability sets, constants
models.py            Frozen dataclasses for moderation results
media_utils.py       Download media, image format conversion, ffmpeg frame extraction
llm_moderator.py     Core moderation logic, API routing, JSON response parsing
output_formatter.py  Generate results.json, summary.txt, results.xlsx
```

All modules import `converse_with_model()` and `bedrock_client` from the parent project's `aws_clients.py` via `importlib` to avoid naming conflicts.
