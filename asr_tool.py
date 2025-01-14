import json
import os

import boto3

from config import WHISPER_ENDPOINT_NAME
# from tools.bedrock_text_tool import region_name


def call_sagemaker(endpoint_name, audio_data):
    sagemaker_runtime = boto3.client('sagemaker-runtime',region_name='us-east-1')
    # 调用 SageMaker endpoint
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='audio/x-audio',
        Body=audio_data
    )

    # 解析响应
    return json.loads(response['Body'].read().decode())


def asr_local_file(endpoint_name, local_file):
    print(f"音频ASR文件地址为{local_file}")
    if not os.path.exists(local_file):
        print(f"音频文件不存在: {local_file}")
        return ""

    file_size = os.path.getsize(local_file)
    if file_size == 0:
        print(f"音频文件为空: {local_file}")
        return ""

    # 读取音频文件
    with open(local_file, 'rb') as audio_file:
        audio_data = audio_file.read()

    if not audio_data:
        print("音频文件为空。。。。")
        return ""

    else:
        result = call_sagemaker(endpoint_name, audio_data)
        print(result)
        return json.dumps(result,ensure_ascii=False)




def asr_s3(endpoint_name, bucket, key):
    '''
        调用sagemaker_endpoint获取文本
        :return:
        '''
    # 初始化 S3 和 SageMaker runtime 客户端
    s3 = boto3.client('s3',region_name='us-east-1')

    try:
        # 从 S3 下载文件
        tmp_file_path = '/tmp/' + os.path.basename(key)
        s3.download_file(bucket, key, tmp_file_path)

        # 读取音频文件
        with open(tmp_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        result = call_sagemaker(endpoint_name, audio_data)
        # 清理临时文件
        os.remove(tmp_file_path)

        return json.dumps(result)

    except Exception as e:
        print(f"Error: {str(e)}")
        return json.dumps(str(e))


if __name__ == '__main__':
    # SageMaker endpoint 名称
    # endpoint_name = "huggingface-pytorch-inference-2024-11-24-01-37-22-758"

    '''
    s3文件测试asr
    '''
    # 从事件中获取 S3 桶和对象键
    # bucket = "media-library-lee"
    # key = "origin_media_vp/sample1.flac"
    # print(asr_s3(endpoint_name, bucket, key))
    import threading
    import time

    '''
    本地文件测试asr
    '''
    # local_file="sample1.flac"
    # local_file="audio/black.flac"
    local_file= "/ffmpeg_output2/03.wav"
    print(asr_local_file(WHISPER_ENDPOINT_NAME, local_file))


