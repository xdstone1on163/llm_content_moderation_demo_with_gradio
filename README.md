# Multimedia Content Transcription and Moderation System Demo

## Project Overview

This is a multimedia content moderation and transcription system demo based on AWS services, providing the following core functionalities:

1. **Image Moderation**
   - Uses large language models and Amazon Rekognition to detect inappropriate content in images
   - Processing time tracking for both LLM and Rekognition to compare speed and efficiency
   - Supports identification of violence, adult content, offensive images, etc.

2. **Video Moderation**
   - Supports two analysis methods:
     * Frame-based analysis: Extracts and analyzes key frames using large language models
     * Direct video understanding: Uses AWS Bedrock Nova models to analyze entire videos without frame extraction
   - **AWS Rekognition Video Content Moderation**: Runs in parallel with LLM analysis for side-by-side comparison
   - Processing time tracking for both LLM and Rekognition to compare speed and efficiency
   - Provides detailed content risk assessment and insights

3. **Video Stream Moderation**
   - Uses camera to capture real-time video stream
   - Supports custom frame capture and analysis frequency
   - Performs content moderation and analysis on captured video frames

4. **Audio Transcription and Toxicity Detection**
   - Uses AWS Transcribe for multilingual audio transcription
   - Performs toxicity content detection for English audio
   - Identifies potentially harmful voice content

5. **Text Moderation**
   - Uses large language models and AWS Comprehend to analyze sensitive or inappropriate content in text

6. **Batch Content Moderation (Headless CLI)**
   - Located in `automated_execution_without_UI/` — no Gradio UI needed
   - Reads test cases from Excel (text/image/video) and runs LLM-based moderation via AWS Bedrock
   - Supports 20+ models: Claude, Nova, DeepSeek, Qwen, Kimi, GLM series
   - Models grouped by capability: text-only, text+image, text+image+video
   - Smart routing: Converse API for Claude/Nova, InvokeModel (OpenAI-compatible) for Kimi K2.5
   - Nova models auto-fallback: direct video understanding fails → frame-based analysis
   - 5 moderation categories: pornography, violence, tobacco/alcohol, political sensitivity, profanity
   - Bilingual prompts (Chinese/English) with `--lang zh|en`
   - Output: `results.json`, `summary.txt`, `results.xlsx` (4 sheets with color-coded severity)
   - CLI: `python automated_execution_without_UI/main.py -m <model_id> [--text-only|--image-only|--video-only]`

## Supported Models and Pricing

All models are available via AWS Bedrock on-demand pricing (us-west-2, standard tier, per 1M tokens).

### Text + Image + Video (Direct Video Understanding)

| Model | Model ID | Input $/1M | Output $/1M | Provider |
|-------|----------|----------:|------------:|----------|
| Nova 2 Lite | `us.amazon.nova-2-lite-v1:0` | $0.33 | $2.75 | Amazon |
| Nova Lite | `us.amazon.nova-lite-v1:0` | $0.06 | $0.24 | Amazon |
| Nova Pro | `us.amazon.nova-pro-v1:0` | $0.80 | $3.20 | Amazon |
| Nova Premier | `us.amazon.nova-premier-v1:0` | $2.50 | $12.50 | Amazon |

### Text + Image (Video via Frame Extraction)

| Model | Model ID | Input $/1M | Output $/1M | Provider | API |
|-------|----------|----------:|------------:|----------|-----|
| Claude Haiku 4.5 | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | $1.00 | $5.00 | Anthropic | Converse |
| Claude Sonnet 4 | `global.anthropic.claude-sonnet-4-20250514-v1:0` | $3.00 | $15.00 | Anthropic | Converse |
| Claude Sonnet 4.5 | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | $3.00 | $15.00 | Anthropic | Converse |
| Claude Sonnet 4.6 | `global.anthropic.claude-sonnet-4-6` | $3.00 | $15.00 | Anthropic | Converse |
| Claude Opus 4.5 | `global.anthropic.claude-opus-4-5-20251101-v1:0` | $5.00 | $25.00 | Anthropic | Converse |
| Claude Opus 4.6 | `global.anthropic.claude-opus-4-6-v1` | $5.00 | $25.00 | Anthropic | Converse |
| Claude Opus 4.1 | `global.anthropic.claude-opus-4-1-20250805-v1:0` | $15.00 | $75.00 | Anthropic | Converse |
| Qwen3 VL 235B | `qwen.qwen3-vl-235b-a22b` | $0.53 | $2.66 | Qwen | Converse |
| Kimi K2.5 | `moonshotai.kimi-k2.5` | $0.60 | $3.00 | Moonshot AI | InvokeModel |

### Text Only

| Model | Model ID | Input $/1M | Output $/1M | Provider |
|-------|----------|----------:|------------:|----------|
| Nova Micro | `us.amazon.nova-micro-v1:0` | $0.035 | $0.14 | Amazon |
| GLM 4.7 Flash | `zai.glm-4.7-flash` | $0.07 | $0.40 | Z.AI |
| Qwen3 Next 80B | `qwen.qwen3-next-80b-a3b` | $0.14 | $1.20 | Qwen |
| Kimi K2 Thinking | `moonshot.kimi-k2-thinking` | $0.60 | $2.50 | Moonshot AI |
| GLM 4.7 | `zai.glm-4.7` | $0.60 | $2.20 | Z.AI |
| DeepSeek V3.2 | `deepseek.v3.2` | $0.62 | $1.85 | DeepSeek |
| DeepSeek R1 | `deepseek-llm-r1` | $0.62 | $1.85 | DeepSeek |

> Note: Global (`global.*`) and US (`us.*`) profiles for the same model share the same pricing. Prices sourced from AWS Pricing API (us-west-2, standard tier, March 2026).

## Interface Screenshots
**Image Moderation Interface:**
<img width="1328" alt="Screenshot 2025-03-01 at 5 21 18 PM" src="https://github.com/user-attachments/assets/77ebe253-00c3-46ac-9ac8-f15644466a81" />
**Video Moderation Interface:**
<img width="1347" alt="Screenshot 2025-03-01 at 5 21 32 PM" src="https://github.com/user-attachments/assets/b7c516f8-914b-48c5-97de-071a5a9c61d8" />
**Video Stream Moderation Interface:**
<img width="1327" alt="Screenshot 2025-03-01 at 5 21 42 PM" src="https://github.com/user-attachments/assets/0c560b5b-fdcf-4b00-8842-6b2974332986" />
**Audio/Video Transcription Interface:**
<img width="1338" alt="Screenshot 2025-03-01 at 5 22 00 PM" src="https://github.com/user-attachments/assets/662748d9-5c5d-4618-b5ac-39134ebae8d1" />
**Text Moderation Interface:**
<img width="1336" alt="Screenshot 2025-03-01 at 5 21 50 PM" src="https://github.com/user-attachments/assets/881185e5-3fde-47f5-834b-ac8ae9056102" />

## Technology Stack

- Python 3.8+
- AWS SDK (boto3)
- Gradio (Web interface)
- Amazon Rekognition (Image + Video Content Moderation)
- Amazon Transcribe
- Amazon Comprehend

## Environment Dependencies

### Required System Dependencies
- Python 3.8+
- pip
- ffmpeg
- git

## Deploying the Project on macOS

### 1. Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install System Dependencies
```bash
brew install python@3.11 ffmpeg git
```

### 3. Clone the Project
```bash
git clone https://github.com/xdstone1on163/llm_content_moderation_demo_with_gradio.git
cd llm_content_moderation_demo_with_gradio
```

### 4. Configure Conda Virtual Environment (https://docs.anaconda.com/miniconda/install/)
```bash
conda create -n myenv python=3.11
conda activate myenv
```

### 5. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 6. AWS Credentials Configuration
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-west-2
# Default output format: json
```

### 7. Run the Application
```bash
python main.py
```

## Configuration File Description

### config.py
The config.py file contains the main configuration parameters for the project, including:
- Model prompts
- Model list and price configuration
- S3 bucket name
- Other system default parameters

Example:
```python
# S3 bucket configuration
S3_BUCKET_NAME = "your-bucket-name"

# Model configurations
MODEL_LIST = ["model1", "model2"]
```

### .env File
The project supports using a .env file to configure sensitive information and environment variables. Create a .env file in the project root directory:
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2

# S3 Configuration (optional, will override settings in config.py)
S3_BUCKET_NAME=your-bucket-name
```

Note:
- The .env file contains sensitive information and is configured to be ignored in .gitignore, it will not be committed to the version control system
- Environment variable values will override default settings in config.py
- It is recommended to use the .env file for local development and system environment variables in production
- Also ensure that you have enabled permissions for Claude/Nova and other related models through the Bedrock service in your AWS region

## AWS Service Configuration

### Required IAM Permissions
Ensure the IAM role includes the following policies:
- AmazonRekognitionFullAccess
- AmazonTranscribeFullAccess
- AmazonComprehendFullAccess
- AmazonS3FullAccess
- AWSBedrockFullAccess (for Nova model access)

### AWS Bedrock Configuration
1. Ensure you have access to AWS Bedrock in your region
2. Enable the following models in AWS Bedrock:
   - Claude models for frame-based analysis
   - Nova Lite and Pro models for direct video understanding

## Security Considerations

1. Always configure IAM roles using the principle of least privilege
2. Rotate AWS access keys regularly
3. Do not commit sensitive credentials to the version control system

## License

[Choose and add an appropriate open-source license, such as MIT, Apache 2.0, etc.]

## Contribution Guidelines

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact Information

[xdstone1@163.com]

---

**Note**: This project is for learning and research purposes only. Please comply with relevant laws and regulations, and respect copyright and privacy.
