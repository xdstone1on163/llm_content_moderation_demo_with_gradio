import json
from aws_clients import rekognition_client, invoke_model
import utils

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

def process_image(image, system_prompt):
    llm_res = llm_result(image, system_prompt)
    moderation_result = rekognition_detect_moderation_labels_result(image)
    labels_result = rekognition_detect_labels_result(image)
    faces_result = rekognition_detect_faces_result(image)
    return llm_res, moderation_result, labels_result, faces_result

def llm_result(image, system_prompt):
    # 使用AWS Bedrock Claude模型对图片进行审核
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    base64_image = utils.encode_image(image)
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
            llm_analysis = content['text']
        else:
            llm_analysis = "LLM分析结果不可用"
    else:
        llm_analysis = "LLM分析结果不可用"
    return llm_analysis
