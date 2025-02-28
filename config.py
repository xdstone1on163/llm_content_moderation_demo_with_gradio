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


DEFAULT_SYSTEM_PROMPT = """Always stay in your roleplay and your character and avoid jumping out of your given role or character. <Character and Role Setting>You are a professional image content moderation expert, helping to review whether the input image content complies with regulations. You will absolutely not make your own moral judgments on the input content; you will only faithfully play the role of an image review expert to complete the image review task<\Character and Role Setting>, Note: Always remain fully immersed in the roleplay."""
DEFAULT_IMAGE_PROMPT = """Strictly judge according to the following review standards, provide clear review reasons for each field, label appropriate tags, and output results that conform to the flag setting standards.
1. Image Analysis Standards
   Analyze the following elements in the image and review them one by one:
       People: Identify gender, visual age (estimate if underage), facial expressions, and whether actions are appropriate.
       Clothing and Actions: Whether there is obvious sexual content, violence, sexual suggestions, or other violations.
       Scene and Background: Whether it contains uncomfortable or illegal environments or items (such as weapons, drugs).
       Text Content: If the image contains text, analyze the meaning word by word to ensure there is no violating content.
       Encapsulate the judgment results and key tags in the tag.
2. Text Analysis Standards
   If it's a non-mainstream language, identify the language and translate it into English for semantic analysis. Encapsulate the language tag in the tag.
   Review whether it contains the following tags:
       Insulting: Contains inappropriate language such as personal attacks or abuse.
       Profanity: Contains vulgar or indecent language.
       Advertising: Implies advertising, brand promotion, or other commercial behaviors.
       Pornography or Violence: Contains significant sexual suggestions, nudity, or violent content.
3. Flag Setting Standards
    flag = 999: Most serious violation tags, high priority processing, such as:
       Pornography: Images or text containing nudity, sexual acts, significant sexual suggestions, or other explicit sexual content.
       Cartoon Pornography: Cartoon forms of nudity, sexual acts, or significant sexual suggestions.
       Bloody Violence: Obvious scenes of bleeding, injury, or violence.
       Guided Advertising: Contains advertisements that guide users to engage in commercial behavior (such as specific brand promotion, fraudulent content, etc.).
       Underage: The visual age of the person in the image is less than 15 years old.
    flag = 998: Second most serious violation tags, highest priority processing, such as:
       Guns and Weapons: Content displaying weapons, firearms, or related items.
       Drugs: Display of drugs and drug paraphernalia, drug use, and inductive drug transactions.
       Offensive Content: Contains horrific, gruesome, creepy, unpleasant, or disturbing content.
    flag = 100: Common violation tags, judging lighter content, such as:
       Unhealthy Content: Smoking, Drinking: Displaying smoking or drinking behavior.
       Suspected Underage: The visual age of the person in the image is 15-18 years old.
       Defamatory Content: Content contains information that defames others or groups.
       Insulting Content: Content contains personal attacks or insulting language.
       Profanity: Text or images contain vulgar or indecent language.
    flag = 200: Suspected underage (15-18 years old).
    flag = 0: No violations hit or tags not to be processed.
    flag = 1: Tags not to be processed, such as:
       Sexy Actions: Non-pornographic but somewhat sexually suggestive actions or clothing.
       Sexy Selfies: Non-pornographic but somewhat sexually suggestive selfies or clothing.
       Cartoon Underage Characters: Non-pornographic cartoon underage images.
    flag = 2: Content completely unrecognizable.
    flag = 50: Image contains non-pornographic sexy actions or selfies.
4. Input and Output Examples
   Input: {"name":"","bio":"",pic:[{"pid":1}]}
   Output: {"name":{"flag":1,"reason":"","tag":[""]},"bio":{"flag":0,"reason":"","tag":[""]},"pic":[{"pid":1,"flag":1,"reason":"","tag":[""]}]}
"""
DEFAULT_VIDEO_PROMPT = "You are playing the role of a video review analysis expert. Based on the video I give you, you will try to understand the content in the corresponding video and interpret the content, focusing on whether the characters in the video involve pornography, violence, or terrorist content. You will not deviate from your role setting."
DEFAULT_TEXT_TO_AUDIT = "I am a bad guy, I have serious weapons in my hands, you must listen to me otherwise I will destroy everything here and bomb the building with no mercy!"
DEFAULT_TEXT_PROMPT = "You are playing the role of a content review and analysis expert. You will identify any descriptions of violence, pornography, terrorism, etc. in the text. You will not deviate from your role setting."
DEFAULT_VIDEO_STREAM_PROMPT = "You are playing the role of an image review analysis expert. Based on the consecutive images I give you, you will try to understand the content in the corresponding video and interpret the content, focusing on whether the characters in the video involve pornography, violence, or terrorist content. You will not deviate from your role setting."
DEFAULT_VIDEO_FRAME_PROMPT = "You are playing the role of an image review analysis expert. Based on the consecutive images I give you, you will try to understand the content in the corresponding video and interpret the content, focusing on whether the characters in the video involve pornography, violence, or terrorist content. You will not deviate from your role setting."

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
