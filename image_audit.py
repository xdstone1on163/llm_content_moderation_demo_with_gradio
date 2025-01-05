import json
import io
import os
import cv2
from aws_clients import rekognition_client, invoke_model, converse_with_model
import utils
import config
import numpy as np
from PIL import Image
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_IMAGE_PROMPT

def rekognition_detect_moderation_labels_result(image):
    image_bytes = utils.get_image_bytes(image)
    response = rekognition_client.detect_moderation_labels(
        Image={'Bytes': image_bytes},
    )
    labels = [label['Name'] + f" ({label['Confidence']:.2f}%)" for label in response['ModerationLabels']]
    return "Moderation Labels:\n" + "\n".join(labels)

def rekognition_detect_labels_result(image):
    image_bytes = utils.get_image_bytes(image)
    response = rekognition_client.detect_labels(
        Image={'Bytes': image_bytes},
    )
    labels = [label['Name'] + f" ({label['Confidence']:.2f}%)" for label in response['Labels']]
    return "Detected Labels:\n" + "\n".join(labels)

def rekognition_detect_faces_result(image):
    image_bytes = utils.get_image_bytes(image)
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

def process_image(image, system_prompt, model_id):
    llm_res = llm_result(image, system_prompt, model_id)
    moderation_result = rekognition_detect_moderation_labels_result(image)
    labels_result = rekognition_detect_labels_result(image)
    faces_result = rekognition_detect_faces_result(image)
    return llm_res, moderation_result, labels_result, faces_result

def llm_result(image, system_prompt, model_id):
    """使用选定的模型对图片进行审核"""
    try:
        # Use the same image handling logic as utils.py
        if isinstance(image, str):
            # If image is a file path
            if os.path.isfile(image):
                with Image.open(image) as img:
                    image = img.copy()
            else:
                raise ValueError(f"File not found: {image}")
        elif isinstance(image, np.ndarray):
            # Convert NumPy array to PIL Image
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        elif not isinstance(image, Image.Image):
            raise ValueError("Unsupported image type. Expected PIL Image, NumPy array, or file path.")
        
        # Convert image to bytes
        image_bytes = utils.get_image_bytes(image)
        
        # Prepare messages
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": DEFAULT_IMAGE_PROMPT+",here is my audit result："
                    },
                    {
                        "image": {
                            "format": "jpeg",
                            "source": {
                                "bytes": image_bytes
                            }
                        }
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [{"text": "```json"}]
            }
        ]
        
        # Prepare system prompts
        system_prompts = [{"text": system_prompt}] if system_prompt else None
        
        # Use the converse API
        llm_analysis = converse_with_model(
            model_id=model_id,
            system_prompts=system_prompts,
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
            top_p=0.9
        )
        return llm_analysis
        
    except Exception as e:
        print(f"LLM分析错误: {str(e)}")
        return "LLM分析结果不可用"
