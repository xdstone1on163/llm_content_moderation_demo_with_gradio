import gradio as gr
from image_audit import process_image
from video_audit import process_video
from text_audit import process_text
from audio_audit import create_audio_interface
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_VIDEO_PROMPT, DEFAULT_TEXT_PROMPT
import cv2
import threading
import time
import os
import glob

# Global variables for video capture
capture_interval = 3  # Capture a frame every 3 seconds
is_running = False
capture_thread = None
latest_captured_frame_path = None

# Ensure the directory for storing frames exists
FRAME_STORAGE_DIR = os.path.join(os.getcwd(), 'captured_images')
os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)

def get_video_stream():
    return cv2.VideoCapture(0)

def capture_frames():
    global is_running, latest_captured_frame_path
    cap = get_video_stream()
    frame_count = 0
    while is_running:
        ret, frame = cap.read()
        if not ret:
            break

        # Capture a frame every specified interval
        if frame_count % (capture_interval * 30) == 0:  # Assuming 30fps
            filename = os.path.join(FRAME_STORAGE_DIR, f"snapshot_{time.time()}.jpg")
            cv2.imwrite(filename, frame)
            latest_captured_frame_path = filename
            print(f"保存了帧: {filename}")

        frame_count += 1
        time.sleep(1/30)  # Simulate 30fps

    cap.release()

def start_capture_thread():
    global is_running, capture_thread
    is_running = True
    capture_thread = threading.Thread(target=capture_frames)
    capture_thread.daemon = True
    capture_thread.start()

def stop_capture_thread():
    global is_running
    is_running = False
    if capture_thread:
        capture_thread.join()

def update_captured_frame_path():
    global latest_captured_frame_path
    return gr.update(value=latest_captured_frame_path)

def get_captured_frames():
    captured_frames = glob.glob(os.path.join(FRAME_STORAGE_DIR, "snapshot_*.jpg"))
    captured_frames.sort(key=os.path.getmtime, reverse=True)
    return captured_frames

with gr.Blocks() as demo:
    gr.Markdown("## 内容审核 Demo")
    
    with gr.Tabs() as tabs:
        with gr.TabItem("图片审核"):
            image_input = gr.Image(type="pil", label="上传图片", interactive=True)
            system_prompt_input = gr.Textbox(label="LLM图片多模态分析自定义系统提示词", value=DEFAULT_SYSTEM_PROMPT, lines=5)
            llm_output = gr.Textbox(label="LLM 结果")
            
            with gr.Group() as rekognition_group:
                gr.Markdown("Rekognition审核结果")
                with gr.Row():
                    rekognition_moderation_output = gr.Textbox(label="审核标签")
                    rekognition_labels_output = gr.Textbox(label="检测标签")
                    rekognition_faces_output = gr.Textbox(label="检测人脸")
            
            submit_button = gr.Button("分析图片")

        with gr.TabItem("视频审核"):
            gr.Markdown("请使用下面的视频组件上传视频文件或录制视频。上传的视频不要超过200MB。")
            video_input = gr.Video(label="上传或录制视频")
            num_frames_input = gr.Slider(minimum=1, maximum=20, step=1, value=5, label="抽取帧数")
            video_prompt_input = gr.Textbox(label="视频内容审核提示词", value=DEFAULT_VIDEO_PROMPT, lines=5)
            video_output = gr.Gallery(label="抽取的视频帧", columns=20, height="auto")
            video_result = gr.Textbox(label="处理结果")
            video_analysis = gr.Textbox(label="视频内容分析")
            video_submit_button = gr.Button("处理视频")

        with gr.TabItem("视频流截取"):
            gr.Markdown("使用摄像头捕获视频流并截取帧")
            video_stream_output = gr.Image(label="视频流")
            captured_frames_output = gr.Textbox(label="已截取帧的保存路径")
            
            start_capture_button = gr.Button("开始截帧")
            stop_capture_button = gr.Button("停止截帧")

            gr.Markdown("更新已截取帧路径")
            update_path_button = gr.Button("更新已截取帧路径")

            gr.Markdown("已捕获的帧")
            captured_frames_gallery = gr.Gallery(label="已捕获的帧", columns=5, height="auto")

            def start_capture():
                start_capture_thread()
                return gr.update(value="开始截帧")

            def stop_capture():
                stop_capture_thread()
                captured_frames = get_captured_frames()
                return gr.update(value="停止截帧"), gr.update(value=captured_frames)

            start_capture_button.click(fn=start_capture, inputs=[], outputs=[captured_frames_output])
            stop_capture_button.click(fn=stop_capture, inputs=[], outputs=[captured_frames_output, captured_frames_gallery])
            update_path_button.click(fn=update_captured_frame_path, inputs=[], outputs=[captured_frames_output])

        with gr.TabItem("音视频转录"):
            gr.Markdown("请使用下面的组件上传音频/视频文件或录制音频。支持从视频文件中提取音频。")
            audio_components = create_audio_interface()

        with gr.TabItem("文本审核"):
            text_input = gr.Textbox(label="输入待审核文本", lines=5)
            text_prompt_input = gr.Textbox(label="文本审核提示词", value=DEFAULT_TEXT_PROMPT, lines=5)
            text_submit_button = gr.Button("审核文本")
            llm_text_output = gr.Textbox(label="大模型分析结果")
            
            with gr.Group() as comprehend_group:
                gr.Markdown("Comprehend的处理结果")
                with gr.Row():
                    sentiment_output = gr.Textbox(label="情感分析")
                    entities_output = gr.Textbox(label="实体识别")
                    key_phrases_output = gr.Textbox(label="关键短语")
                    pii_entities_output = gr.Textbox(label="个人敏感信息")
                    toxic_content_output = gr.Textbox(label="有害内容检测")

        submit_button.click(
            fn=process_image,
            inputs=[image_input, system_prompt_input],
            outputs=[llm_output, 
                     rekognition_moderation_output, 
                     rekognition_labels_output, 
                     rekognition_faces_output]
        )

        video_submit_button.click(
            fn=process_video,
            inputs=[video_input, num_frames_input, video_prompt_input],
            outputs=[video_output, video_result, video_analysis]
        )

        text_submit_button.click(
            fn=process_text,
            inputs=[text_input, text_prompt_input],
            outputs=[llm_text_output, 
                     sentiment_output, entities_output, 
                     key_phrases_output, pii_entities_output, 
                     toxic_content_output]
        )

demo.queue()
demo.launch(share=True)
