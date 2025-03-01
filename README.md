# Multimedia Content Transcription and Moderation System Demo

## Project Overview

This is a multimedia content moderation and transcription system demo based on AWS services, providing the following core functionalities:

1. **Image Moderation**
   - Uses large language models and Amazon Rekognition to detect inappropriate content in images
   - Supports identification of violence, adult content, offensive images, etc.

2. **Video Moderation**
   - Supports two analysis methods:
     * Frame-based analysis: Extracts and analyzes key frames using large language models
     * Direct video understanding: Uses AWS Bedrock Nova models to analyze entire videos without frame extraction
   - Provides detailed content risk assessment and insights
   - Allows comparison between frame-based and direct analysis approaches

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
- Amazon Rekognition
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
