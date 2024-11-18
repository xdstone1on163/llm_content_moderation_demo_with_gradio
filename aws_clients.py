import boto3

# Initialize AWS clients with specific region
region = 'us-west-2'  # Using us-west-2 region

# Initialize AWS clients
rekognition_client = boto3.client('rekognition', region_name=region)
comprehend_client = boto3.client('comprehend', region_name=region)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
transcribe_client = boto3.client('transcribe', region_name=region)
s3_client = boto3.client('s3', region_name=region)

def invoke_model(body, contentType, accept, modelId):
    response = bedrock_client.invoke_model(
        body=body,
        contentType=contentType,
        accept=accept,
        modelId=modelId
    )
    return response

def start_transcription_job(job_name, media_file_uri, language_code=None, detect_toxicity=True):
    """
    Start an AWS Transcribe job with toxicity detection
    
    Args:
        job_name (str): Unique name for the transcription job
        media_file_uri (str): S3 URI of the media file
        language_code (str, optional): Specific language code
        detect_toxicity (bool, optional): Enable toxicity detection. Defaults to True.
    
    Returns:
        dict: Transcription job response
    """
    try:
        job_args = {
            'TranscriptionJobName': job_name,
            'Media': {'MediaFileUri': media_file_uri},
            'MediaFormat': 'wav',
            'Settings': {
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2
            }
        }

        # For toxicity detection, always use English
        if detect_toxicity:
            job_args['LanguageCode'] = 'en-US'
            job_args['ToxicityDetection'] = [{
                'ToxicityCategories': ['ALL']
            }]
        elif language_code:
            job_args['LanguageCode'] = language_code

        response = transcribe_client.start_transcription_job(**job_args)
        return response
    except Exception as e:
        raise Exception(f"启动转录任务失败: {str(e)}")

def get_transcription_job(job_name):
    """Get the status and results of a transcription job"""
    try:
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        return response
    except Exception as e:
        raise Exception(f"获取转录任务状态失败: {str(e)}")
