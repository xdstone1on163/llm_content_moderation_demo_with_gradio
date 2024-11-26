import subprocess
import os
import tempfile
from PIL import Image
import utils
import config
import json
from aws_clients import invoke_model
import cv2

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
    # Prepare the content for Claude
    content = [{"type": "text", "text": prompt}]
    for i, frame in enumerate(frames):
        base64_image = utils.encode_image(frame)
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
        "modelId": config.MODEL_ID,
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
    response = invoke_model(
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

def process_video_stream(analysis_prompt, frame_interval):
    cap = cv2.VideoCapture(0)  # Open the default camera
    return cap, analysis_prompt, frame_interval
