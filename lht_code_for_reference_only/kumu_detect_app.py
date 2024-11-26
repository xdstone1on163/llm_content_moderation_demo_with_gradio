import boto3
import os
import time
import shutil
from botocore.exceptions import ClientError

def detect_faces(image_path):
    client = boto3.client('rekognition')

    try:
        with open(image_path, 'rb') as image_file:
            image_bytes = image_file.read()
            response = client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )

        face_details = response['FaceDetails']
        
        if len(face_details) > 0:
            print(f"{image_path}: 检测到 {len(face_details)} 张人脸。")
            for i, face in enumerate(face_details, start=1):
                print(f"  人脸 {i}:")
                print(f"    - 置信度: {face['Confidence']:.2f}%")
                print(f"    - 年龄范围: {face['AgeRange']['Low']}-{face['AgeRange']['High']} 岁")
                print(f"    - 性别: {face['Gender']['Value']} (置信度: {face['Gender']['Confidence']:.2f}%)")
                print(f"    - 情绪: {max(face['Emotions'], key=lambda x: x['Confidence'])['Type']}")
        else:
            print(f"{image_path}: 未检测到人脸。")

        return True

    except ClientError as e:
        print(f"处理 {image_path} 时发生错误: {e}")
        return False

def scan_directory(input_dir, archive_dir, interval=60):
    while True:
        print(f"扫描目录: {input_dir}")
        for root, dirs, files in os.walk(input_dir):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_path = os.path.join(root, filename)
                    if detect_faces(image_path):
                        # 如果成功处理，移动到归档目录
                        relative_path = os.path.relpath(root, input_dir)
                        archive_subdir = os.path.join(archive_dir, relative_path)
                        os.makedirs(archive_subdir, exist_ok=True)
                        archive_path = os.path.join(archive_subdir, filename)
                        shutil.move(image_path, archive_path)
                        print(f"已将 {image_path} 移动到 {archive_path}")
                    else:
                        print(f"处理 {image_path} 失败，保留在原目录")

        print(f"等待 {interval} 秒后进行下一次扫描...")
        time.sleep(interval)

# 使用示例
if __name__ == "__main__":
    input_directory = "./captured_frames"
    archive_directory = "./processed_frames"
    
    # 确保归档目录存在
    os.makedirs(archive_directory, exist_ok=True)

    # 开始扫描
    scan_directory(input_directory, archive_directory, interval=30)
