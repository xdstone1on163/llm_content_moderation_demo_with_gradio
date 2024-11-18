import io
import base64
from PIL import Image

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
