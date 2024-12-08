# 多媒体内容转录与审核系统

## 项目简介

这是一个基于AWS服务的多媒体内容审核与转录系统，提供以下核心功能：

1. **图像审核**
   - 使用大语言模型和Amazon Rekognition检测图像中的不适当内容
   - 支持识别暴力、成人内容、冒犯性图像等

2. **视频审核**
   - 使用大语言模型分析视频中的不适当内容
   - 提供详细的内容风险评估

3. **视频流审核**
   - 使用摄像头捕获实时视频流
   - 支持自定义截帧频率和分析频率
   - 对截取的视频帧进行内容审核和分析

4. **音频转录与毒性检测**
   - 使用AWS Transcribe进行多语言音频转录
   - 对英文音频进行毒性内容检测
   - 识别潜在的有害语音内容

5. **文本审核**
   - 使用大语言模型和AWS Comprehend分析文本中的敏感或不适当内容

## 界面截图
**图片审核界面：**
<img width="1189" alt="Screenshot 2024-11-29 at 5 49 41 PM" src="https://github.com/user-attachments/assets/1514699b-93ba-4b80-9e66-6ca83e46a40d">
**视频审核界面：**
<img width="1210" alt="Screenshot 2024-11-29 at 5 49 52 PM" src="https://github.com/user-attachments/assets/501ad79d-3df3-44ba-869b-a402eaba1bd7">
**视频流审核界面：**
<img width="1127" alt="Screenshot 2024-12-09 at 6 08 04 AM" src="https://github.com/user-attachments/assets/764865cb-fed0-405b-b9a1-03e970705f78">
**音视频转录界面：**
<img width="1187" alt="Screenshot 2024-11-29 at 5 50 18 PM" src="https://github.com/user-attachments/assets/a0ec8297-5864-433f-84bf-9f8d61669153">
**文本审核界面：**
<img width="1212" alt="Screenshot 2024-11-29 at 5 50 26 PM" src="https://github.com/user-attachments/assets/baada4a6-960b-4d93-bbef-106e0dc6d796">

## 技术栈

- Python 3.8+
- AWS SDK (boto3)
- Gradio (Web界面)
- Amazon Rekognition
- Amazon Transcribe
- Amazon Comprehend

## 环境依赖

### 必要的系统依赖
- Python 3.8+
- pip
- ffmpeg
- git

### Python依赖包
```bash
pip install gradio boto3 numpy requests
```

## 部署步骤（AWS Linux 2023 EC2）

### 1. 准备EC2实例
1. 选择Amazon Linux 2023 AMI
2. 实例类型建议：
   - 最小：t2.medium
   - 推荐：t3.large
3. 配置安全组，开放：
   - SSH (22端口)
   - HTTP (80端口)
   - HTTPS (443端口)

### 2. 连接到EC2实例
```bash
ssh -i your-key.pem ec2-user@your-instance-ip
```

### 3. 系统更新与基础软件安装
```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git ffmpeg
```

### 4. 配置Python虚拟环境
```bash
python3 -m venv content_moderation_env
source content_moderation_env/bin/activate
```

### 5. 克隆项目
```bash
git clone https://github.com/your-username/llm_content_moderation_demo_with_gradio.git
cd llm_content_moderation_demo_with_gradio
```

### 6. 安装Python依赖
```bash
pip install -r requirements.txt
```

### 7. AWS凭证配置
```bash
aws configure
# 输入您的AWS Access Key ID
# 输入您的AWS Secret Access Key
# 默认区域：us-west-2
# 默认输出格式：json
```

### 8. 运行应用
```bash
python main.py
```

## AWS服务配置

### 必要的IAM权限
确保IAM角色包含以下策略：
- AmazonRekognitionFullAccess
- AmazonTranscribeFullAccess
- AmazonComprehendFullAccess
- AmazonS3FullAccess

## 安全注意事项

1. 始终使用最小权限原则配置IAM角色
2. 定期轮换AWS访问密钥
3. 不要将敏感凭证提交到版本控制系统

## 许可证

[选择并添加适当的开源许可证，如MIT、Apache 2.0等]

## 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m '添加了某某特性'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 联系方式

[xdstone1@163.com]

---

**注意**：本项目仅供学习和研究使用，请遵守相关法律法规，尊重版权和隐私。
