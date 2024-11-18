import gradio as gr
import boto3
import io
import base64
import json
import subprocess
import os
import tempfile
from PIL import Image

rekognition_client = boto3.client('rekognition')
bedrock_client = boto3.client('bedrock-runtime')

def encode_image(image):
    buffered = io.BytesIO()
    image_format = image.format if image.format is not None else 'JPEG'
    image_format = 'PNG' if image_format.lower() == 'png' else 'JPEG'
    image.save(buffered, format=image_format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_image_bytes(image):
    image_bytes = io.BytesIO()
    image_format = image.format if image.format is not None else 'JPEG'
    image_format = 'JPEG' if image_format.lower() in ['jpg', 'jpeg'] else 'PNG'
    image.save(image_bytes, format=image_format)
    return image_bytes.getvalue()

def rekognition_detect_moderation_labels_result(image):
    image_bytes = get_image_bytes(image)
    response = rekognition_client.detect_moderation_labels(
        Image={'Bytes': image_bytes},
    )
    labels = [label['Name'] + f" ({label['Confidence']:.2f}%)" for label in response['ModerationLabels']]
    return "Moderation Labels:\n" + "\n".join(labels)

def rekognition_detect_labels_result(image):
    image_bytes = get_image_bytes(image)
    response = rekognition_client.detect_labels(
        Image={'Bytes': image_bytes},
    )
    labels = [label['Name'] + f" ({label['Confidence']:.2f}%)" for label in response['Labels']]
    return "Detected Labels:\n" + "\n".join(labels)

def rekognition_detect_faces_result(image):
    image_bytes = get_image_bytes(image)
    response = rekognition_client.detect_faces(
        Image={'Bytes': image_bytes},
        Attributes=['ALL']
    )
    face_details = response['FaceDetails']
    result = []
    for i, face in enumerate(face_details, 1):
        result.append(f"Face {i}:")
        result.append(f"  Confidence: {face['Confidence']:.2f}%")
        result.append(f"  Gender: {face['Gender']['Value']} ({face['Gender']['Confidence']:.2f}%)")
        result.append(f"  Age Range: {face['AgeRange']['Low']}-{face['AgeRange']['High']} years")
        emotions = sorted(face['Emotions'], key=lambda x: x['Confidence'], reverse=True)
        result.append(f"  Top Emotion: {emotions[0]['Type']} ({emotions[0]['Confidence']:.2f}%)")
    return "Detected Faces:\n" + "\n".join(result)

DEFAULT_SYSTEM_PROMPT = """你今天扮演的角色是一个图片审核的AI专家，你需要协助人类进行图片审核的工作，你审核图片的标准如下
1. 图片需要是真人，女生，五官清晰，五官端正，图片包含有完整的脸部内容，
2. 图片不能够只露出眼睛，不能带面罩和口罩
2. 图片不能是动漫风格、不能男女混合（不能出现男性）、不能出现小孩、不能是纯风景
3. 图片不能太小，也就是图片的分辨率要高，同时尺寸不能小于480*768
4. 图片除非裸露了胸部和下体才可以判定为不通过，如果只是露出肩膀，露出肚脐，露出大腿和小腿这些都属于可以判定为通过，也就是整体构图不露骨就可以通过
5. 图片严禁涉及血腥、政治的题材，但是如果只是穿着和宗教风俗有关的衣服，其他方面没有问题，应该判为通过
你的输出请按照下面的json格式给出,如果不通过，请给出原因:
{ "结果" = "通过" or "不通过",
  "图片描述" = "xxxxxx",
  "不通过的原因" = "xxxx"
}
"""

DEFAULT_VIDEO_PROMPT = """你是一个视频内容审核专家。我会给你一系列按时间顺序排列的视频帧图片。请根据这些图片分析整个视频的内容，并判断视频是否包含不适当的内容。

请特别注意以下几点：
1. 视频主要在讲述什么内容？
2. 视频中是否存在色情、暴力或恐怖主义相关的内容？
3. 视频的整体基调是什么？是否适合所有年龄段观看？

请提供详细的分析，并给出你的最终判断。如果发现任何不适当的内容，请具体说明是在哪些帧中出现的。

你的回答应该包括以下几个部分：
1. 视频内容概述
2. 对每个关键帧的分析
3. 是否存在不适当内容的判断
4. 总体评估和建议

请用中文回答。
"""

def llm_result(image, system_prompt):
    # 使用AWS Bedrock Claude模型对图片进行审核
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    base64_image = encode_image(image)
    payload = {
        "modelId": model_id,
        "contentType": "application/json",
        "accept": "application/json",
        "body": {
            "anthropic_version": "bedrock-2023-05-31",
            "system": system_prompt,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png" if image.format and image.format.lower() == 'png' else "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": "这是我审查的结果："
                        }
                    ]
                }
            ]
        }
    }

    # Convert the payload to bytes
    body_bytes = json.dumps(payload['body']).encode('utf-8')

    # Invoke the model
    response = bedrock_client.invoke_model(
        body=body_bytes,
        contentType=payload['contentType'],
        accept=payload['accept'],
        modelId=payload['modelId']
    )

    # Process the response
    response_body = json.loads(response['body'].read().decode('utf-8'))
    if 'content' in response_body and isinstance(response_body['content'], list):
        content = response_body['content'][0]
        if 'text' in content:
            llm_analysis = content['text']
        else:
            llm_analysis = "LLM分析结果不可用"
    else:
        llm_analysis = "LLM分析结果不可用"
    return llm_analysis

def process_image(image, system_prompt):
    llm_res = llm_result(image, system_prompt)
    moderation_result = rekognition_detect_moderation_labels_result(image)
    labels_result = rekognition_detect_labels_result(image)
    faces_result = rekognition_detect_faces_result(image)
    return llm_res, moderation_result, labels_result, faces_result

def extract_frames(video_path, num_frames):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract frames using ffmpeg
        output_pattern = os.path.join(temp_dir, "frame_%04d.jpg")
        subprocess.run([
            "ffmpeg", "-i", video_path, 
            "-vf", f"select='not(mod(n,{max(1, int(video_info(video_path)['nb_frames'] / num_frames))}))' ,scale=320:240", 
            "-vsync", "vfr", "-q:v", "2", "-frames:v", str(num_frames), output_pattern
        ], check=True)

        # Read the extracted frames
        frames = []
        for i in range(1, num_frames + 1):
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.jpg")
            if os.path.exists(frame_path):
                with Image.open(frame_path) as img:
                    frames.append(img.copy())

    return frames

def video_info(video_path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", 
        "-count_packets", "-show_entries", "stream=nb_read_packets", 
        "-of", "csv=p=0", video_path
    ], capture_output=True, text=True)
    nb_frames = int(result.stdout.strip())
    return {"nb_frames": nb_frames}

def analyze_video_content(frames, prompt):
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    # Prepare the content for Claude
    content = [{"type": "text", "text": prompt}]
    for i, frame in enumerate(frames):
        base64_image = encode_image(frame)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64_image
            }
        })
        content.append({"type": "text", "text": f"Frame {i+1}"})

    payload = {
        "modelId": model_id,
        "contentType": "application/json",
        "accept": "application/json",
        "body": {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }
    }

    # Convert the payload to bytes
    body_bytes = json.dumps(payload['body']).encode('utf-8')

    # Invoke the model
    response = bedrock_client.invoke_model(
        body=body_bytes,
        contentType=payload['contentType'],
        accept=payload['accept'],
        modelId=payload['modelId']
    )

    # Process the response
    response_body = json.loads(response['body'].read().decode('utf-8'))
    if 'content' in response_body and isinstance(response_body['content'], list):
        content = response_body['content'][0]
        if 'text' in content:
            analysis = content['text']
        else:
            analysis = "视频内容分析结果不可用"
    else:
        analysis = "视频内容分析结果不可用"
    return analysis

def process_video(video, num_frames, prompt):
    if video is None:
        return None, "请先上传视频", None

    try:
        frames = extract_frames(video, int(num_frames))
        analysis = analyze_video_content(frames, prompt)
        return frames, f"成功提取 {len(frames)} 帧并完成内容分析", analysis
    except Exception as e:
        return None, f"处理视频时出错: {str(e)}", None

with gr.Blocks() as demo:
    gr.Markdown("## 内容审核 Demo")
    
    with gr.Tabs() as tabs:
        with gr.TabItem("图片审核"):
            image_input = gr.Image(type="pil", label="上传图片", interactive=True)
            system_prompt_input = gr.Textbox(label="LLM图片多模态分析自定义系统提示词", value=DEFAULT_SYSTEM_PROMPT, lines=5)
            llm_output = gr.Textbox(label="LLM 结果")
            with gr.Row():
                rekognition_moderation_output = gr.Textbox(label="Rekognition Moderation Labels")
                rekognition_labels_output = gr.Textbox(label="Rekognition Detected Labels")
                rekognition_faces_output = gr.Textbox(label="Rekognition Detected Faces")
            submit_button = gr.Button("分析图片")
        
        with gr.TabItem("视频审核"):
            gr.Markdown("请使用下面的视频组件上传视频文件或录制视频。上传的视频不要超过200MB。")
            video_input = gr.Video(label="上传或录制视频")
            num_frames_input = gr.Slider(minimum=1, maximum=20, step=1, value=5, label="抽取帧数")
            video_prompt_input = gr.Textbox(label="视频内容审核提示词", value=DEFAULT_VIDEO_PROMPT, lines=5)
            video_output = gr.Gallery(label="抽取的视频帧", columns=20, height="auto")
            video_result = gr.Textbox(label="处理结果")
            video_analysis = gr.Textbox(label="视频内容分析")
            video_submit_button = gr.Button("处理视频")
        
        with gr.TabItem("文本审核"):
            gr.Markdown("文本审核功能正在开发中...")
        
        with gr.TabItem("音频审核"):
            gr.Markdown("音频审核功能正在开发中...")

    submit_button.click(
        fn=process_image,
        inputs=[image_input, system_prompt_input],
        outputs=[llm_output, rekognition_moderation_output, rekognition_labels_output, rekognition_faces_output]
    )

    video_submit_button.click(
        fn=process_video,
        inputs=[video_input, num_frames_input, video_prompt_input],
        outputs=[video_output, video_result, video_analysis]
    )

demo.launch(share=True)
