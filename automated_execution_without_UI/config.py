import importlib.util
import os

# Import MODEL_LIST and MODEL_PRICES from the parent project's config.py
_parent_config_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
_spec = importlib.util.spec_from_file_location("parent_config", _parent_config_path)
_parent_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent_config)

MODEL_LIST = _parent_config.MODEL_LIST
MODEL_PRICES = _parent_config.MODEL_PRICES

DEFAULT_MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Model capability sets — used for routing and validation
# ---------------------------------------------------------------------------

# Text only — cannot process images or video
TEXT_ONLY_MODELS = set(_parent_config._MODELS_TEXT_ONLY)

# Text + Image via Converse API — can process images; video via frame extraction
TEXT_IMAGE_MODELS = set(_parent_config._MODELS_TEXT_IMAGE)

# Text + Image via InvokeModel API (OpenAI-compatible, base64 image in message)
INVOKE_MODEL_IMAGE_MODELS = set(_parent_config._MODELS_TEXT_IMAGE_INVOKE)

# Text + Image + Video — supports direct video understanding (Nova)
DIRECT_VIDEO_MODELS = set(_parent_config._MODELS_TEXT_IMAGE_VIDEO)

MEDIA_DOWNLOAD_TIMEOUT = 60
VIDEO_FRAME_COUNT = 5
DEFAULT_LANG = "zh"

# ---------------------------------------------------------------------------
# JSON response template (shared across languages, keys always English)
# ---------------------------------------------------------------------------

_JSON_TEMPLATE = """\
```json
{
  "categories": {
    "pornography": {"detected": false, "severity": "none", "details": ""},
    "violence": {"detected": false, "severity": "none", "details": ""},
    "tobacco_alcohol": {"detected": false, "severity": "none", "details": ""},
    "political_sensitivity": {"detected": false, "severity": "none", "details": ""},
    "profanity": {"detected": false, "severity": "none", "details": ""}
  },
  "overall_risk": "safe",
  "summary": ""
}
```"""

_SEVERITY_NOTE_EN = 'Severity levels: "none", "low", "medium", "high"\nOverall risk levels: "safe", "low", "medium", "high", "critical"'
_SEVERITY_NOTE_ZH = '严重程度(severity): "none"(无), "low"(低), "medium"(中), "high"(高)\n总体风险(overall_risk): "safe"(安全), "low"(低), "medium"(中), "high"(高), "critical"(极高)'

# ---------------------------------------------------------------------------
# Bilingual prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS = {
    "zh": (
        "你是一名专业的内容审核专家。你需要从以下五个类别分析内容是否违规："
        "色情、暴力、烟酒、政治敏感、污言秽语。"
        "你必须仅返回一个有效的JSON对象，不要包含任何其他文字。"
        "始终保持客观和全面的分析。"
        "重要：JSON中的key必须使用英文，但details和summary字段的值必须使用中文。"
    ),
    "en": (
        "You are a professional content moderation expert. You analyze content for policy violations "
        "across five categories: pornography, violence, tobacco/alcohol, political sensitivity, and profanity. "
        "You MUST respond ONLY with a valid JSON object, no other text. "
        "Always remain objective and thorough in your analysis."
    ),
}

_TEXT_PROMPTS = {
    "zh": """分析以下文本是否存在内容审核违规。

审核类别：
1. **pornography（色情）**: 性内容、裸露描写、露骨的性暗示
2. **violence（暴力）**: 身体伤害描写、威胁、血腥、武器
3. **tobacco_alcohol（烟酒）**: 推广或美化吸烟、饮酒、药物滥用
4. **political_sensitivity（政治敏感）**: 涉及中国领导人（习近平、毛泽东等）、中国地缘政治（台湾、西藏、香港、新疆）、批评中共、天安门、法轮功、涉及独裁/专制/极权/威权/暴政/集权统治等描述或指控、煽动颠覆政权、分裂国家
5. **profanity（污言秽语）**: 脏话、骂人、侮辱性语言、人身攻击、威胁恐吓、低俗粗鄙表达

仅返回以下JSON结构（key使用英文，details和summary使用中文）：
{json_template}

{severity_note}

待审核文本：
""",
    "en": """Analyze the following text for content moderation violations.

Categories to check:
1. **pornography**: Sexual content, nudity descriptions, explicit sexual references
2. **violence**: Descriptions of physical harm, threats, gore, weapons
3. **tobacco_alcohol**: Promotion or glorification of smoking, drinking, drug use
4. **political_sensitivity**: References to Chinese leaders (Xi Jinping, Mao Zedong, etc.), Chinese geopolitics (Taiwan, Tibet, Hong Kong, Xinjiang), CCP criticism, Tiananmen, Falun Gong, accusations or descriptions of dictatorship/authoritarianism/totalitarianism/tyranny/autocracy, incitement to subvert state power or secession
5. **profanity**: Swearing, cursing, insults, personal attacks, threatening language, vulgar or obscene expressions

Respond with ONLY this JSON structure:
{json_template}

{severity_note}

Text to analyze:
""",
}

_IMAGE_PROMPTS = {
    "zh": """分析此图片是否存在内容审核违规。

审核类别：
1. **pornography（色情）**: 裸露、性内容、性暗示的姿势或服装
2. **violence（暴力）**: 武器、血腥、暴力、身体伤害、威胁性图像
3. **tobacco_alcohol（烟酒）**: 吸烟、饮酒、药物使用、物质推广
4. **political_sensitivity（政治敏感）**: 中国领导人（习近平、毛泽东、胡锦涛、江泽民等）、政治符号、抗议图像、涉及中国的敏感地缘政治内容、涉及独裁/专制/极权/威权/暴政等描述的文字或标语
5. **profanity（污言秽语）**: 图片中包含的脏话、侮辱性文字、威胁性文字、低俗粗鄙文字内容

仅返回以下JSON结构（key使用英文，details和summary使用中文）：
{json_template}

{severity_note}
""",
    "en": """Analyze this image for content moderation violations.

Categories to check:
1. **pornography**: Nudity, sexual content, sexually suggestive poses or clothing
2. **violence**: Weapons, blood, gore, physical harm, threatening imagery
3. **tobacco_alcohol**: Smoking, drinking, drug use, promotion of substances
4. **political_sensitivity**: Chinese leaders (Xi Jinping, Mao Zedong, Hu Jintao, Jiang Zemin, etc.), political symbols, protest imagery, sensitive geopolitical content involving China, text or slogans describing dictatorship/authoritarianism/totalitarianism/tyranny
5. **profanity**: Swearing, insults, threatening text, vulgar or obscene text content visible in the image

Respond with ONLY this JSON structure:
{json_template}

{severity_note}
""",
}

_VIDEO_PROMPTS = {
    "zh": """分析此视频内容是否存在内容审核违规。

审核类别：
1. **pornography（色情）**: 裸露、性内容、性暗示动作
2. **violence（暴力）**: 武器、血腥、暴力、身体伤害、打斗、威胁行为
3. **tobacco_alcohol（烟酒）**: 吸烟、饮酒、药物使用、物质推广
4. **political_sensitivity（政治敏感）**: 中国领导人（习近平、毛泽东、胡锦涛、江泽民等）、政治事件、抗议画面、涉及中国的敏感地缘政治内容（台湾、西藏、香港、新疆）、涉及独裁/专制/极权/威权/暴政等描述（包括语音和画面文字）
5. **profanity（污言秽语）**: 视频中出现的脏话、骂人、侮辱性语言、威胁恐吓、低俗粗鄙表达（包括语音和画面文字）

仅返回以下JSON结构（key使用英文，details和summary使用中文）：
{json_template}

{severity_note}
""",
    "en": """Analyze this video content for content moderation violations.

Categories to check:
1. **pornography**: Nudity, sexual content, sexually suggestive actions
2. **violence**: Weapons, blood, gore, physical harm, fighting, threatening behavior
3. **tobacco_alcohol**: Smoking, drinking, drug use, substance promotion
4. **political_sensitivity**: Chinese leaders (Xi Jinping, Mao Zedong, Hu Jintao, Jiang Zemin, etc.), political events, protest footage, sensitive geopolitical content involving China (Taiwan, Tibet, Hong Kong, Xinjiang), descriptions of dictatorship/authoritarianism/totalitarianism/tyranny in audio or on-screen text
5. **profanity**: Swearing, cursing, insults, threatening language, vulgar or obscene expressions in audio or on-screen text

Respond with ONLY this JSON structure:
{json_template}

{severity_note}
""",
}


def get_prompts(lang="zh"):
    """Return (system_prompt, text_prompt, image_prompt, video_prompt) for the given language."""
    lang = lang if lang in ("zh", "en") else "zh"
    severity = _SEVERITY_NOTE_ZH if lang == "zh" else _SEVERITY_NOTE_EN
    fmt = {"json_template": _JSON_TEMPLATE, "severity_note": severity}
    return (
        _SYSTEM_PROMPTS[lang],
        _TEXT_PROMPTS[lang].format(**fmt),
        _IMAGE_PROMPTS[lang].format(**fmt),
        _VIDEO_PROMPTS[lang].format(**fmt),
    )
