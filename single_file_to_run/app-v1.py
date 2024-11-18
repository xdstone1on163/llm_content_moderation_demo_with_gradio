import gradio as gr
import boto3
import io
import base64
import json

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

with gr.Blocks() as demo:
    gr.Markdown("## 图片审核 Demo")
    with gr.Column():
        image_input = gr.Image(type="pil", label="上传图片", interactive=True)
        system_prompt_input = gr.Textbox(label="LLM图片多模态分析自定义系统提示词", value=DEFAULT_SYSTEM_PROMPT, lines=5)
        llm_output = gr.Textbox(label="LLM 结果")
    with gr.Row():
        rekognition_moderation_output = gr.Textbox(label="Rekognition Moderation Labels")
        rekognition_labels_output = gr.Textbox(label="Rekognition Detected Labels")
        rekognition_faces_output = gr.Textbox(label="Rekognition Detected Faces")
    submit_button = gr.Button("分析图片")

    def process_image(image, system_prompt):
        llm_res = llm_result(image, system_prompt)
        moderation_result = rekognition_detect_moderation_labels_result(image)
        labels_result = rekognition_detect_labels_result(image)
        faces_result = rekognition_detect_faces_result(image)
        return llm_res, moderation_result, labels_result, faces_result

    submit_button.click(fn=process_image, inputs=[image_input, system_prompt_input], outputs=[llm_output, rekognition_moderation_output, rekognition_labels_output, rekognition_faces_output])

demo.launch(share=True)
