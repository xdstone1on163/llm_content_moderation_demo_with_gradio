import subprocess
import os
import time
from datetime import datetime

def capture_frames(stream_url, output_dir, interval=5, duration=60, wait_time=300):
    while True:
        try:
            # 创建以时间戳命名的子目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_output_dir = os.path.join(output_dir, timestamp)
            os.makedirs(current_output_dir, exist_ok=True)

            output_pattern = os.path.join(current_output_dir, "frame_%d.jpg")

            ffmpeg_cmd = [
                '/home/ec2-user/SageMaker/yeahmobi/kreadoAI/re_train_wav2lip-on-sagemaker/ffmpeg-git-20240301-amd64-static/ffmpeg',
                '-i', stream_url,
                '-vf', f'fps=1/{interval}',
                '-frames:v', str(duration // interval),
                '-y',  # 覆盖现有文件
                output_pattern
            ]

            print(f"开始新一轮捕获，时间: {timestamp}")
            print("执行的 FFmpeg 命令:", ' '.join(ffmpeg_cmd))

            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            start_time = time.time()
            while process.poll() is None:
                if time.time() - start_time > duration + 10:  # 给予额外的10秒
                    print("FFmpeg 执行超时")
                    process.terminate()
                    break
                time.sleep(1)

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                print(f"FFmpeg 命令执行成功")
            else:
                print("FFmpeg 命令执行失败")

            print("标准输出:", stdout.decode())
            print("错误输出:", stderr.decode())

            # 检查是否生成了图片
            generated_frames = [f for f in os.listdir(current_output_dir) if f.endswith('.jpg')]
            print(f"生成的图片数量: {len(generated_frames)}")

        except Exception as e:
            print('发生错误:', str(e))

        print(f"等待 {wait_time} 秒后开始下一轮捕获...")
        time.sleep(wait_time)

# 使用示例
if __name__ == "__main__":
    stream_url = "https://0c9eff39f978.us-west-2.playback.live-video.net/api/video/v1/us-west-2.517141035927.channel.Og4DwhYAtxGT.m3u8"
    output_dir = "captured_frames"
    capture_frames(stream_url, output_dir, interval=5, duration=60, wait_time=30)  # 每5分钟捕获一次，每次持续60秒
