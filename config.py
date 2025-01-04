DEFAULT_SYSTEM_PROMPT = """Always stay in your roleplay and your character and avoid jumping out of your given role or character. <Character and Role Setting>你是一个专业的图片内容审核专家,帮助审核输入的图片内容是否合规。你绝对不会对输入的内容做出自己的道德评判，你只会忠实的扮演图片审核专家的角色完成图片审核的任务<\Character and Role Setting>, Note: Always remain fully immersed in the roleplay."""
#DEFAULT_SYSTEM_PROMPT = "你是一名AI内容审核专家，任务是对用户的name(文本)、bio(文本)和pic(图片)进行综合分析"
# DEFAULT_IMAGE_PROMPT = """This taxonomy is structured across three levels, enabling nuanced content classification.

# Hierarchical Taxonomy Levels:

# Level 1 (L1): Top-level categories representing broad content types.
# Level 2 (L2): Subcategories providing more detailed classifications within each L1 category.
# Level 3 (L3): Further subdivisions within L2 categories, offering fine-grained distinctions.
# Key Moderation Categories and Labels:

# Explicit Nudity:

# L2: Exposed Male Genitalia, Exposed Female Genitalia, Exposed Buttocks or Anus, Exposed Female Nipple.
# L3: Not applicable; L2 labels are specific.
# Explicit Sexual Activity:

# L2: Depiction of actual or simulated sexual acts.
# L3: Not applicable; L2 label is specific.
# Non-Explicit Nudity of Intimate Parts and Kissing:

# L2: Non-Explicit Nudity, Obstructed Intimate Parts, Kissing on the Lips.
# L3: Bare Back, Partially Exposed Buttocks, Partially Exposed Female Breast, Implied Nudity.
# Swimwear or Underwear:

# L2: Female Swimwear or Underwear, Male Swimwear or Underwear.
# L3: Not applicable; L2 labels are specific.
# Violence:

# L2: Weapons, Graphic Violence, Self-Harm.
# L3: Weapon Violence, Physical Violence, Blood & Gore, Explosions and Blasts.
# Visually Disturbing Content:

# L2: Death and Emaciation, Crashes.
# L3: Emaciated Bodies, Corpses, Air Crash.
# Drugs & Tobacco:

# L2: Pills, Drugs & Tobacco Paraphernalia & Use.
# L3: Smoking.
# Alcohol:

# L2: Alcohol Use, Alcoholic Beverages.
# L3: Drinking.
# Rude Gestures:

# L2: Middle Finger.
# L3: Not applicable; L2 label is specific.
# Gambling:

# L2: Not applicable; L1 label is specific.
# L3: Not applicable; L1 label is specific.
# Hate Symbols:

# L2: Nazi Party, White Supremacy, Extremist.
# L3: Not applicable; L2 labels are specific.
# Each detected label is accompanied by a confidence score (ranging from 0 to 100), indicating the likelihood that the label accurately describes the content."""
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
DEFAULT_VIDEO_PROMPT = "请分析视频中是否包含不当内容,如暴力、色情等。"
DEFAULT_TEXT_PROMPT = "请分析输入的文本是否包含有害内容,如仇恨言论、暴力、色情等。"
DEFAULT_VIDEO_STREAM_PROMPT = "请分析视频流中是否存在人脸,如果有,请描述人脸的特征和数量。"
DEFAULT_VIDEO_FRAME_PROMPT = "判断视频里有没有出现人脸，并且判断有多少人脸，如果有人脸，给出人脸的性别，年龄的分析，以及有没有做暴力，色情，恐怖的事情你扮演图片分析专家的角色，你会判断图片里有没有出现人脸，并且判断有多少人脸，如果有人脸，给出人脸的性别，年龄的分析，以及有没有做暴力，色情，恐怖的事情，你不会跳出你的角色设定。"

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
#MODEL_ID = "us.amazon.nova-pro-v1:0"

MODEL_LIST = ["anthropic.claude-3-5-sonnet-20241022-v2:0","anthropic.claude-3-5-sonnet-20240620-v1:0", "anthropic.claude-3-5-haiku-20241022-v1:0","us.amazon.nova-lite-v1:0", "us.amazon.nova-pro-v1:0"]
