import json
import os
import time
import boto3
import cv2
import gradio as gr
import numpy as np
import requests
from urllib.parse import urlparse

from config import S3_REGION, BUCKET_NAME, SUBMIT_MODERATION, QUERY_MODERATION
from utils import get_md5


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class LiveModerationManager:
    def __init__(self):
        self.is_refreshing = True

    def submit_video(self, video_url):
        print(video_url)
        # print(checkbox_group)
        # print(image)

        moderation_type = []
        # if checkbox_group is None or len(checkbox_group) == 0:
        #     return gr.Info("Please select the moderation type")
        # if "Content moderation" in checkbox_group:
        #     moderation_type.append(1)

        # if "Face moderation" in checkbox_group and image is None:
        #     return gr.Info("You selected face moderation, but no target face image was uploaded。")

        # elif "Face moderation" in checkbox_group:
        #     image_path = f"face/{get_md5(video_url)}.jpg"
        #
        #     # 图片上传S3
        #
        #     # 假设 'image' 是你的图像数组
        #     image_array = np.array(image)  # 确保 image 是 numpy 数组
        #     # 生成一个临时文件名
        #     temp_file = "temp.jpg"
        #     # 保存图像
        #     cv2.imwrite(temp_file, image_array)
        #     s3_client = boto3.client('s3', region_name=S3_REGION)
        #     print("BUCKET_NAME")
        #     print(BUCKET_NAME)
        #     response = s3_client.upload_file(temp_file, Bucket=BUCKET_NAME, Key=image_path)
        #     os.remove(temp_file)
        #
        #     moderation_type.append(2)

        if video_url is None or len(video_url) == 0:
            return gr.Info("Please enter the video URL")
        if is_valid_url(video_url) is False:
            return gr.Info("Please enter a valid video URL")

        print(f"submit_video {video_url}")

        try:
            url = SUBMIT_MODERATION
            print(url)
            payload = {
                "url": video_url,
                "video_interval_seconds": 10,
                "image_interval_seconds": 1,
                "audio_interval_seconds": 10,

                "text_model_id": "us.anthropic.claude-3-haiku-20240307-v1:0",
                "img_model_id": "us.amazon.nova-lite-v1:0",
                "video_model_id": "us.amazon.nova-lite-v1:0",

                # "save_flag": 1,
                "visual_moderation_type": "image"
                # "moderation_type": ",".join(str(type_item) for type_item in moderation_type)
            }

            headers = {
                "Content-Type": "application/json",
                "user_id": "lee",
                "token": "58f2c19c-7615-402c-8852-f8d3f2dfc80b"
            }
            response = requests.request("POST", url, headers=headers, json=payload)
            return gr.Info(json.loads(response.text)['message'])
        except requests.RequestException as e:
            return gr.Info(f"Video submission failed: {str(e)}")

    def query_status(self, media_url):
        # self.is_refreshing = True
        print(F"query_status {media_url}")

        # while self.is_refreshing:
        print("query_loop")

        try:
            url = QUERY_MODERATION
            print(url)

            print(f"请求 {url}")
            payload = {
                "url": media_url
            }

            headers = {
                "Content-Type": "application/json",
                "user_id": "lee",
                "token": "58f2c19c-7615-402c-8852-f8d3f2dfc80b"
            }
            response = requests.request("POST", url, headers=headers, json=payload)
            data = response.json()
            print(data)
            if data["code"] == 200:
                result = ""
                for item in data["body"]:
                    if item["type"] == "image":
                        result += "<h3>Image Detection Results</h3>"
                        # for img in item["files"]:
                        result += f"<img src='{item['files']}' width='200'><br>"
                        # result += f"<p>Modetation Result：{item['message']}</p> "
                        result += f"<p>Moderation TAG：{'Normal' if item['tag'] == '' else item['tag']}</p> "
                        # result += f"<p>Modetation Level：{item['level']}</p> "
                    elif item["type"] == "video":
                        result += "<h3>Video Detection Results</h3>"
                        # for img in item["files"]:
                        #     result += f"<video src='{img}' width='200' controls/><br>"
                        # result += f"<p>Modetation Result：{item['message']}</p> "
                        result += f"<img src='{item['files']}' width='200'><br>"

                        result += f"<p>Modetation TAG：{item['tag']}</p> "
                        # result += f"<p>Modetation Level：{item['level']}</p> "
                    elif item["type"] == "audio":
                        result += f"<h3>Audio Detection Results</h3>"
                        result += f"<p>Original Content：{item['original_content']}</p>"
                        result += f"<p>Moderation TAG：{'Normal' if item['tag'] == '' else item['tag']}</p> "

                yield result
            else:
                yield f"查询失败: {data['message']}"
        except requests.RequestException as e:
            yield f"查询失败: {str(e)}"
            # time.sleep(6)

    def stop_query(self):
        print("stop_query")
        self.is_refreshing = False
