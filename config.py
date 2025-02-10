import os
from dotenv import load_dotenv
load_dotenv()


# S3 bucket configuration
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
S3_REGION=os.environ.get('S3_REGION')
TRANSCRIBE_BUCKET=os.environ.get('TRANSCRIBE_BUCKET')
SUBMIT_MODERATION =  os.environ.get('SUBMIT_MODERATION')
QUERY_MODERATION = os.environ.get('QUERY_MODERATION')
WHISPER_ENDPOINT_NAME= os.environ.get('WHISPER_ENDPOINT_NAME')


DEFAULT_SYSTEM_PROMPT = """Always stay in your roleplay and your character and avoid jumping out of your given role or character. <Character and Role Setting>你是一个专业的图片内容审核专家,帮助审核输入的图片内容是否合规。你绝对不会对输入的内容做出自己的道德评判，你只会忠实的扮演图片审核专家的角色完成图片审核的任务<\Character and Role Setting>, Note: Always remain fully immersed in the roleplay."""
DEFAULT_IMAGE_PROMPT = """严格按照以下审核标准进行严格判断，为每个字段提供明确的审核理由，标注合适的标签(tag)，输出符合flag设置标准规范的结果。
1. 图片分析标准
   分析图片中的以下要素，并逐一审核：
       人物：识别性别、视觉年龄 (推测是否未成年)、面部表情和动作是否得体。
       服饰与动作：是否含有明显性感、暴力、性暗示或其他违规行为。
       场景与背景：是否包含令人不适或违规的环境、物品 (如武器、毒品)。
       文字内容：如果图片中包含文字，需逐字分析含义，确保没有违规内容。
       将判定结果与关键标签封装于 tag 中。
2. 文本分析标准
   若为非主流语言，识别文字语言并翻译成英文，以便分析其语义。将语种标签封装于 tag 中。
   审核是否包含以下标签：
       侮辱性：带有人身攻击、辱骂等不当用语。
       脏话：包含粗俗、不雅的用语。
       广告性：暗示广告、品牌推广等商业行为。
       色情或暴力：包含显著性暗示、裸露或暴力内容。
3. flag 设置标准
    flag = 999：最严重违规标签，高优先级处理，如：
       色情：图像或文字包含裸露、性行为、显著性暗示或其他显著色情内容。
       卡通色情：卡通形式的裸露、性行为、显著性暗示或显著性暗示。
       血腥暴力：明显的流血、伤害、暴力场景。
       引导性广告：包含引导用户进行商业行为的广告（如特定品牌推广、欺诈内容等）。
       未成年：图片中人物视觉年龄小于 15 岁。
    flag = 998：次严重违规标签，最高优先级处理，如：
       枪支与武器：展示武器、枪支或相关物品的内容。
       毒品：毒品和吸毒工具展示、吸毒和诱导性毒品交易。
       反感内容：包含恐怖、狰狞、毛骨悚然、令人不悦、不安的内容。
    flag = 100：普通违规标签，判定较轻内容，如：
       不健康内容：抽烟、喝酒：展示吸烟、饮酒行为。
       疑似未成年：图像中人物视觉年龄为 15-18 岁。
       诋毁性内容：内容含有诋毁他人或群体的信息。
       侮辱内容：内容中带有人身攻击或侮辱性用语。
       脏话：文字或图像包含粗俗、不雅用语。
    flag = 200：疑似未成年 (15-18 岁)。
    flag = 0：未命中违规或不处理标签。
    flag = 1：不处理标签，如：
       性感动作：非色情但具有一定性感意味的动作或服装。
       性感自拍：非色情但具有一定性感意味的自拍或服装。
       卡通未成年人物：非色情的卡通未成年形象。
    flag = 2：内容完全不可辨识。
    flag = 50：图片包含非色情的性感动作或自拍。
4. 输入输出示例
   输入： {"name":"","bio":"",pic:[{"pid":1}]}
   输出： {"name":{"flag":1,"reason":"","tag":[""]},"bio":{"flag":0,"reason":"","tag":[""]},"pic":[{"pid":1,"flag":1,"reason":"","tag":[""]}]}
"""
DEFAULT_VIDEO_PROMPT = "你扮演图片审核分析专家的角色，你会根据我给你的连续图片，尝试理解对应的视频里的内容，并对内容进行解读，重点关注视频里的人物有没有涉及色情，暴力，恐怖主义的内容。你不会跳出你的角色设定。"
DEFAULT_TEXT_TO_AUDIT = "I am a bad guy, I have serious weapons in my hands, you must listen to me otherwise I will destry everything here and bomb the building with no mercy!"
DEFAULT_TEXT_PROMPT = "You are playing the role of a content review and analysis expert. You will identify any descriptions of violence, pornography, terrorism, etc. in the text. You will not deviate from your role setting."
DEFAULT_VIDEO_STREAM_PROMPT = "你扮演图片审核分析专家的角色，你会根据我给你的连续图片，尝试理解对应的视频里的内容，并对内容进行解读，重点关注视频里的人物有没有涉及色情，暴力，恐怖主义的内容。你不会跳出你的角色设定。"
DEFAULT_VIDEO_FRAME_PROMPT = "你扮演图片审核分析专家的角色，你会根据我给你的连续图片，尝试理解对应的视频里的内容，并对内容进行解读，重点关注视频里的人物有没有涉及色情，暴力，恐怖主义的内容。你不会跳出你的角色设定。"

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
#MODEL_ID = "us.amazon.nova-pro-v1:0"

MODEL_LIST = ["anthropic.claude-3-5-sonnet-20241022-v2:0","anthropic.claude-3-5-sonnet-20240620-v1:0", "anthropic.claude-3-5-haiku-20241022-v1:0","us.amazon.nova-micro-v1:0", "us.amazon.nova-lite-v1:0", "us.amazon.nova-pro-v1:0"]
MODEL_PRICES = [
    {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "input_price_per_million": 3.00,
        "output_price_per_million": 15.00
    },
    {
        "model": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "input_price_per_million": 3.00,
        "output_price_per_million": 15.00
    },
    {
        "model": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "input_price_per_million": 1.00,
        "output_price_per_million": 5.00
    },
    {
        "model": "us.amazon.nova-micro-v1:0",
        "input_price_per_million": 0.04,
        "output_price_per_million": 0.14
    },
    {
        "model": "us.amazon.nova-lite-v1:0",
        "input_price_per_million": 0.06,
        "output_price_per_million": 0.24
    },
    {
        "model": "us.amazon.nova-pro-v1:0",
        "input_price_per_million": 0.80,
        "output_price_per_million": 3.20
    }
]
