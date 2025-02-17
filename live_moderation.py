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

    def submit_video(self, video_url, checkbox_group, image):
        print(video_url)
        print(checkbox_group)
        print(image)

        moderation_type = []
        if checkbox_group is None or len(checkbox_group) == 0:
            return gr.Info("Please select the moderation type")
        if "Content moderation" in checkbox_group:
            moderation_type.append(1)

        if "Face moderation" in checkbox_group and image is None:
            return gr.Info("You selected face moderation, but no target face image was uploaded。")

        elif "Face moderation" in checkbox_group:
            image_path = f"face/{get_md5(video_url)}.jpg"

            # 图片上传S3

            # 假设 'image' 是你的图像数组
            image_array = np.array(image)  # 确保 image 是 numpy 数组
            # 生成一个临时文件名
            temp_file = "temp.jpg"
            # 保存图像
            cv2.imwrite(temp_file, image_array)
            s3_client = boto3.client('s3', region_name=S3_REGION)
            print("BUCKET_NAME")
            print(BUCKET_NAME)
            response = s3_client.upload_file(temp_file, Bucket=BUCKET_NAME, Key=image_path)
            os.remove(temp_file)

            moderation_type.append(2)

        if video_url is None or len(video_url) == 0:
            return gr.Info("Please enter the video URL")
        if is_valid_url(video_url) is False:
            return gr.Info("Please enter a valid video URL")

        print(f"submit_video {video_url}")

        try:
            url = SUBMIT_MODERATION
            print(url)
            payload = {"token": "6666",
                       "url": video_url,
                       "moderation_type": ",".join(str(type_item) for type_item in moderation_type)}

            headers = {
                "Content-Type": "application/json"
            }
            response = requests.request("POST", url, headers=headers, json=payload)
            return gr.Info(json.loads(response.text)['message'])
        except requests.RequestException as e:
            return gr.Info(f"Video submission failed: {str(e)}")

    def query_status(self, media_url):
        self.is_refreshing = True
        print(F"query_status {media_url}")

        while self.is_refreshing:
            print("query_loop")
           
            try:
                url =QUERY_MODERATION
                print(url)

                print(f"请求 {url}")
                payload = {
                    "token": "6666",
                    "url": media_url
                }

                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.request("POST", url, headers=headers, json=payload)
                data = response.json()
                print(data)
                if data["code"] == 200:
                    result = ""
                    for item in data["body"]:
                        if item["type"] == "image":
                            result += "<h3>Image Detection Results</h3>"
                            for img in item["images"]:
                                result += f"<img src='{img}' width='200'><br>"
                            result += f"<p>Modetation Result：{item['message']}</p> "
                        elif item["type"] == "audio":
                            result += f"<h3>Audio Detection Results</h3>"
                            result += f"<p>Original Content：{item['original_content']}</p>"
                            result += f"<p>Moderation Result：{item['message']}</p> "

                    yield result
                else:
                    yield f"查询失败: {data['message']}"
            except requests.RequestException as e:
                yield f"查询失败: {str(e)}"
            time.sleep(2)

    def stop_query(self):
        print("stop_query")
        self.is_refreshing = False


