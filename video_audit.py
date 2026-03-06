import subprocess
import os
import tempfile
import io
from PIL import Image
import utils
import config
import json
from aws_clients import invoke_model, converse_with_model
import cv2
import logging
import base64
import time

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

def analyze_video_content(frames, prompt, model_id):
    """Analyze video frame content using the selected model"""
    
    # Prepare the message content with frames
    content = [{"text": prompt}]
    for i, frame in enumerate(frames):
        try:
            # Handle both PIL Image objects and frame paths
            if isinstance(frame, str):
                # If frame is a path, open it as PIL Image
                with Image.open(frame) as img:
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG')
                    image_bytes = img_byte_arr.getvalue()
            else:
                # If frame is already a PIL Image
                img_byte_arr = io.BytesIO()
                frame.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
            content.append({
                "image": {
                    "format": "jpeg",
                    "source": {
                        "bytes": image_bytes
                    }
                }
            })
            content.append({"text": f"Frame {i+1}"})
        except Exception as e:
            logging.error(f"Error encoding frame {i+1}: {str(e)}")
            continue
    
    # Prepare the message for conversation
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    
    # Prepare system prompts
    system_prompts = [{"text": "You are a video content analyzer. Analyze the following video frames and provide insights."}]
    
    # Use the converse API
    try:
        analysis = converse_with_model(
            model_id=model_id,
            system_prompts=system_prompts,
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )
    except Exception as e:
        logging.error(f"Video analysis error: {str(e)}")
        analysis = "Video content analysis result unavailable"
    
    return analysis

def video_direct_understanding(video_path, prompt, model_id, is_s3_path=False):
    """Analyze video content directly using AWS Bedrock Nova model"""
    if video_path is None:
        return "Please upload a video or provide an S3 path", None

    try:
        # Define system prompts
        system_list = [
            {
                "text": "You are an expert video content analyzer. Analyze the video content and provide detailed insights."
            }
        ]
        
        # Define message list with video and prompt
        message_list = [
            {
                "role": "user",
                "content": []
            }
        ]
        
        # For S3 paths, use the s3Location format
        if is_s3_path:
            # Parse S3 path to extract bucket and key
            # Expected format: s3://bucket-name/path/to/video.mp4
            if video_path.startswith("s3://"):
                # Use S3 location format as per AWS documentation
                message_list[0]["content"].append({
                    "video": {
                        "format": "mp4",
                        "source": {
                            "s3Location": {
                                "uri": video_path
                            }
                        }
                    }
                })
                logging.info(f"Using S3 video path: {video_path}")
            else:
                raise ValueError(f"Invalid S3 path format: {video_path}. S3 path must start with 's3://'")
        else:
            # Read local video file as bytes and encode to base64
            with open(video_path, 'rb') as video_file:
                binary_data = video_file.read()
                base_64_encoded_data = base64.b64encode(binary_data)
                base64_string = base_64_encoded_data.decode('utf-8')
            
            message_list[0]["content"].append({
                "video": {
                    "format": "mp4",
                    "source": {"bytes": base64_string}
                }
            })
        
        # Add prompt text
        message_list[0]["content"].append({
            "text": prompt
        })
        
        # Configure inference parameters
        inf_params = {
            "maxTokens": 2000,
            "temperature": 0.3,
            "topP": 0.9,
            "topK": 20
        }
        
        # Prepare the request body
        native_request = {
            "schemaVersion": "messages-v1",
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inf_params
        }
        
        try:
            # Invoke the model
            response = invoke_model(
                body=json.dumps(native_request),
                contentType="application/json",
                accept="application/json",
                modelId=model_id
            )
            
            # Parse the response
            model_response = json.loads(response.get('body').read())
            analysis = model_response["output"]["message"]["content"][0]["text"]
            
        except Exception as e:
            logging.error(f"Video direct analysis error: {str(e)}")
            analysis = "Video content analysis result unavailable"
        
        return "Successfully completed direct video analysis", analysis
    except Exception as e:
        logging.error(f"Error in direct video understanding: {str(e)}")
        return f"Error processing video: {str(e)}", None

def process_video(video, num_frames, prompt, model_id, analysis_method="frame", is_s3_path=False):
    if video is None:
        return None, "Please upload a video or provide an S3 path", None

    try:
        if analysis_method == "frame" and not is_s3_path:
            frames = extract_frames(video, int(num_frames))
            analysis = analyze_video_content(frames, prompt, model_id)
            return frames, f"Successfully extracted {len(frames)} frames and completed content analysis", analysis
        else:  # direct or S3 path
            result_message, analysis = video_direct_understanding(video, prompt, model_id, is_s3_path)
            return None, result_message, analysis
    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        return None, f"Error processing video: {str(e)}", None

def process_video_stream(analysis_prompt, frame_interval):
    cap = cv2.VideoCapture(0)  # Open the default camera
    return cap, analysis_prompt, frame_interval
