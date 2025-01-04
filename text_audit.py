import json
from aws_clients import comprehend_client, invoke_model, converse_with_model
import config

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
    
    # Sentiment Detection
    try:
        sentiment_response = comprehend_client.detect_sentiment(
            Text=text,
            LanguageCode=dominant_language
        )
        sentiment_result = json.dumps({
            "语言": detected_language,
            "情感倾向": sentiment_response['Sentiment'],
            "情感分数": {
                "正面": f"{sentiment_response['SentimentScore']['Positive']:.2%}",
                "负面": f"{sentiment_response['SentimentScore']['Negative']:.2%}",
                "中性": f"{sentiment_response['SentimentScore']['Neutral']:.2%}",
                "混合": f"{sentiment_response['SentimentScore']['Mixed']:.2%}"
            }
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        sentiment_result = json.dumps({
            "错误": f"情感分析不支持该语言 ({dominant_language})"
        }, ensure_ascii=False, indent=2)
    
    # Entities Detection
    try:
        entities_response = comprehend_client.detect_entities(
            Text=text,
            LanguageCode=dominant_language
        )
        entities_result = json.dumps({
            "语言": detected_language,
            "实体": [{"文本": e['Text'], "类型": e['Type']} for e in entities_response['Entities']]
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        entities_result = json.dumps({
            "错误": f"实体识别不支持该语言 ({dominant_language})"
        }, ensure_ascii=False, indent=2)
    
    # Key Phrases Detection
    try:
        key_phrases_response = comprehend_client.detect_key_phrases(
            Text=text,
            LanguageCode=dominant_language
        )
        key_phrases_result = json.dumps({
            "语言": detected_language,
            "关键短语": [kp['Text'] for kp in key_phrases_response['KeyPhrases']]
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        key_phrases_result = json.dumps({
            "错误": f"关键短语提取不支持该语言 ({dominant_language})"
        }, ensure_ascii=False, indent=2)
    
    # PII Entities Detection
    if dominant_language in ['en', 'es']:
        try:
            pii_response = comprehend_client.detect_pii_entities(
                Text=text,
                LanguageCode=dominant_language
            )
            pii_result = json.dumps({
                "语言": detected_language,
                "个人敏感信息": [
                    {
                        "类型": e['Type'],
                        "置信度": f"{e['Score']:.2%}",
                        "起始位置": e['BeginOffset'],
                        "结束位置": e['EndOffset']
                    } for e in pii_response['Entities']
                ]
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            pii_result = json.dumps({
                "错误": f"PII检测失败: {str(e)}"
            }, ensure_ascii=False, indent=2)
    else:
        pii_result = json.dumps({
            "错误": f"PII检测不支持该语言 ({dominant_language})"
        }, ensure_ascii=False, indent=2)
    
    # Toxic Content Detection
    if dominant_language == 'en':
        try:
            # Prepare text segments in the required dictionary format
            text_segments = [
                {"Text": text[i:i+1000]} 
                for i in range(0, len(text), 1000)
            ]
            
            toxic_response = comprehend_client.detect_toxic_content(
                TextSegments=text_segments,
                LanguageCode='en'
            )
            
            toxic_labels = []
            overall_toxicity = 0
            for segment_result in toxic_response.get('ResultList', []):
                # Extract labels from each segment
                segment_toxic_labels = [
                    {
                        "名称": label['Name'],
                        "置信度": f"{label['Score']:.2%}"
                    } for label in segment_result.get('Labels', [])
                ]
                toxic_labels.extend(segment_toxic_labels)
                
                # Track overall toxicity
                overall_toxicity = max(overall_toxicity, segment_result.get('Toxicity', 0))
            
            toxic_result = json.dumps({
                "语言": detected_language,
                "有害内容标签": toxic_labels,
                "总体有害程度": f"{overall_toxicity:.2%}"
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            toxic_result = json.dumps({
                "错误": f"有害内容检测失败: {str(e)}"
            }, ensure_ascii=False, indent=2)
    else:
        toxic_result = json.dumps({
            "错误": f"有害内容检测仅支持英文 (当前语言: {dominant_language})"
        }, ensure_ascii=False, indent=2)
    
    return sentiment_result, entities_result, key_phrases_result, pii_result, toxic_result

def analyze_text_with_llm(text, prompt, model_id):
    """使用选定的模型分析文本内容"""
    
    # Prepare the message for conversation
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": f"{prompt}\n\n文本内容：{text}"
                }
            ]
        },
        {
            "role": "assistant",
            "content": [{"text": "```json"}]
        }
    ]
    
    # Prepare system prompts
    system_prompts = [{"text": "You are a text content analyzer. Analyze the following text and provide insights."}]
    
    # Use the converse API
    try:
        analysis = converse_with_model(
            model_id=model_id,
            system_prompts=system_prompts,
            messages=messages,
            max_tokens=2000,
            temperature=0.3,
            top_p=0.9
        )
    except Exception as e:
        print(f"文本分析错误: {str(e)}")
        analysis = "LLM分析结果不可用"
    
    return analysis

def process_text(text, prompt, model_id):
    llm_analysis = analyze_text_with_llm(text, prompt, model_id)
    
    # Unpack the Comprehend analysis results in the correct order
    sentiment, entities, key_phrases, pii_entities, toxic_content = analyze_text_with_comprehend(text)
    
    return llm_analysis, sentiment, entities, key_phrases, pii_entities, toxic_content
