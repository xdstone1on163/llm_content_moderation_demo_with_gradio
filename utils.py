import io
import base64
from PIL import Image
import cv2
import numpy as np
import logging
import os
import hashlib

def encode_image(image):
    try:
        if isinstance(image, str):
            # If image is a file path
            if os.path.isfile(image):
                with Image.open(image) as img:
                    image = img.copy()
            else:
                raise ValueError(f"File not found: {image}")
        elif isinstance(image, np.ndarray):
            # Convert NumPy array to PIL Image
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        elif not isinstance(image, Image.Image):
            raise ValueError("Unsupported image type. Expected PIL Image, NumPy array, or file path.")

        buffered = io.BytesIO()
        image_format = image.format if image.format is not None else 'JPEG'
        image_format = 'PNG' if image_format.upper() == 'PNG' else 'JPEG'
        image.save(buffered, format=image_format)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encoding image: {e}")
        raise

def get_image_bytes(image):
    try:
        if isinstance(image, str):
            # If image is a file path
            if os.path.isfile(image):
                with Image.open(image) as img:
                    image = img.copy()
            else:
                raise ValueError(f"File not found: {image}")
        elif isinstance(image, np.ndarray):
            # Convert NumPy array to PIL Image
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        elif not isinstance(image, Image.Image):
            raise ValueError("Unsupported image type. Expected PIL Image, NumPy array, or file path.")

        image_bytes = io.BytesIO()
        image_format = image.format if image.format is not None else 'JPEG'
        image_format = 'JPEG' if image_format.upper() in ['JPEG', 'JPG'] else 'PNG'
        image.save(image_bytes, format=image_format)
        return image_bytes.getvalue()
    except Exception as e:
        logging.error(f"Error getting image bytes: {e}")
        raise


def get_md5(input_string):
    # 如果输入是字符串，先编码为 bytes
    if isinstance(input_string, str):
        input_string = input_string.encode('utf-8')

    # 创建 MD5 对象
    md5_hash = hashlib.md5()

    # 更新 MD5 对象with the bytes
    md5_hash.update(input_string)

    # 获取十六进制表示的 MD5 哈希值
    return md5_hash.hexdigest()