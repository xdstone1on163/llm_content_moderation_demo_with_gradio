import json
from aws_clients import comprehend_client, invoke_model
import config

def analyze_text_with_llm(text, prompt):
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
                    "content": f"{prompt}\n\n文本内容：{text}"
                }
            ]
        }
    }

    response = invoke_model(
        body=json.dumps(payload['body']).encode('utf-8'),
        contentType=payload['contentType'],
        accept=payload['accept'],
        modelId=payload['modelId']
    )

    response_body = json.loads(response['body'].read().decode('utf-8'))
    if 'content' in response_body and isinstance(response_body['content'], list):
        content = response_body['content'][0]
        if 'text' in content:
            analysis = content['text']
        else:
            analysis = "LLM分析结果不可用"
    else:
        analysis = "LLM分析结果不可用"
    return analysis

def analyze_text_with_comprehend(text):
    # Detect dominant language
    language_response = comprehend_client.detect_dominant_language(Text=text)
    dominant_language = language_response['Languages'][0]['LanguageCode']
    
    # Map ISO language codes to human-readable names
    language_names = {
        'zh': '中文',
        'en': '英文',
        'ja': '日文',
        'ko': '韩文',
        'es': '西班牙文',
        'fr': '法文',
        'de': '德文',
        'pt': '葡萄牙文',
        'it': '意大利文',
        'ru': '俄文'
    }
    
    detected_language = language_names.get(dominant_language, dominant_language)
    
    # Initialize results dictionary
    results = {
        "DetectedLanguage": f"检测到的语言: {detected_language} ({dominant_language})",
        "LanguageScore": f"语言检测置信度: {language_response['Languages'][0]['Score']:.2%}"
    }
    
    # Perform language-specific analysis if the language is supported
    try:
        # Detect sentiment (supported languages may vary)
        sentiment_response = comprehend_client.detect_sentiment(
            Text=text,
            LanguageCode=dominant_language
        )
        results["Sentiment"] = sentiment_response['Sentiment']
        results["SentimentScores"] = sentiment_response['SentimentScore']
    except Exception as e:
        results["Sentiment"] = f"情感分析不支持该语言 ({dominant_language})"
        results["SentimentScores"] = {}
    
    try:
        # Detect entities
        entities_response = comprehend_client.detect_entities(
            Text=text,
            LanguageCode=dominant_language
        )
        results["Entities"] = [{"Text": e['Text'], "Type": e['Type']} for e in entities_response['Entities']]
    except Exception as e:
        results["Entities"] = []
        results["EntitiesError"] = f"实体识别不支持该语言 ({dominant_language})"
    
    try:
        # Detect key phrases
        key_phrases_response = comprehend_client.detect_key_phrases(
            Text=text,
            LanguageCode=dominant_language
        )
        results["KeyPhrases"] = [kp['Text'] for kp in key_phrases_response['KeyPhrases']]
    except Exception as e:
        results["KeyPhrases"] = []
        results["KeyPhrasesError"] = f"关键短语提取不支持该语言 ({dominant_language})"
    
    # Detect PII entities (only supported in English and Spanish)
    if dominant_language in ['en', 'es']:
        try:
            pii_response = comprehend_client.detect_pii_entities(
                Text=text,
                LanguageCode=dominant_language
            )
            pii_entities = [
                {
                    "Type": e['Type'],
                    "Score": e['Score'],
                    "BeginOffset": e['BeginOffset'],
                    "EndOffset": e['EndOffset']
                } for e in pii_response['Entities']
            ]
            pii_summary = "发现以下类型的个人敏感信息: " + ", ".join(set(e['Type'] for e in pii_entities)) if pii_entities else "未发现个人敏感信息"
        except Exception as e:
            pii_entities = []
            pii_summary = f"PII检测失败: {str(e)}"
    else:
        pii_entities = []
        pii_summary = f"PII检测不支持该语言 ({dominant_language})"
    
    results["PIIEntities"] = pii_entities
    results["PIISummary"] = pii_summary
    
    return json.dumps(results, ensure_ascii=False, indent=2)

def process_text(text, prompt):
    llm_analysis = analyze_text_with_llm(text, prompt)
    comprehend_analysis = analyze_text_with_comprehend(text)
    return llm_analysis, comprehend_analysis
