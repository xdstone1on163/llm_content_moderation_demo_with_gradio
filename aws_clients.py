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

def converse_with_model(model_id, system_prompts, messages, max_tokens=2000, temperature=0.3, top_p=0.9):
    """
    Start or continue a conversation using Bedrock's Converse API
    
    Args:
        model_id (str): The model ID to use
        system_prompts (list): List of system prompts
        messages (list): List of message dictionaries with role and content
        max_tokens (int): Maximum number of tokens in response
        temperature (float): Temperature for response generation
        top_p (float): Top P for response generation
    
    Returns:
        str: Model's response text
    """
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            system=system_prompts,
            messages=messages,
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": top_p,
                "stopSequences": ["```"], # stop sequences here
            }
        )
        
        result = response['output']['message']['content'][0]['text']
        result = result.rstrip("`")
        print("Using model: "+model_id)
        return result
    except Exception as e:
        print(f"Model invocation error: {str(e)}")
        return "Model invocation error"

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
        raise Exception(f"Failed to start transcription job: {str(e)}")

def get_transcription_job(job_name):
    """Get the status and results of a transcription job"""
    try:
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        return response
    except Exception as e:
        raise Exception(f"Failed to get transcription job status: {str(e)}")
