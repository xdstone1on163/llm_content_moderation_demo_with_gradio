import gradio as gr
from image_audit import process_image
from video_audit import process_video, analyze_video_content
from text_audit import process_text
from audio_audit import create_audio_interface
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_VIDEO_PROMPT, DEFAULT_TEXT_PROMPT, DEFAULT_VIDEO_FRAME_PROMPT
import cv2
import threading
import time
import os
import glob
import queue
import shutil

# Global variables for video capture
capture_interval = 1  # Capture a frame every 1 second
is_running = False
is_analyzing = False
capture_thread = None
analysis_thread = None
latest_captured_frame_path = None
log_queue = queue.Queue()
log_content = ""
analysis_output = ""

# Ensure the directory for storing frames exists
FRAME_STORAGE_DIR = os.path.join(os.getcwd(), 'captured_images')
os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)

def get_video_stream():
    return cv2.VideoCapture(0)

def capture_frames(capture_rate):
    global is_running, latest_captured_frame_path, log_content
    cap = get_video_stream()
    frame_count = 0
    while is_running:
        ret, frame = cap.read()
        if not ret:
            break

        # Capture a frame every specified interval
        if frame_count % (capture_rate * 30) == 0:  # Assuming 30fps
            filename = os.path.join(FRAME_STORAGE_DIR, f"snapshot_{time.time()}.jpg")
            cv2.imwrite(filename, frame)
            latest_captured_frame_path = filename
            log_message = f"成功截取帧: {filename}"
            print(log_message)
            log_content += log_message + "\n"
            log_queue.put(log_message)

        frame_count += 1
        time.sleep(1/30)  # Simulate 30fps

    cap.release()

def start_capture_thread(capture_rate):
    global is_running, capture_thread
    is_running = True
    
    # Clear the captured frames directory
    for filename in os.listdir(FRAME_STORAGE_DIR):
        file_path = os.path.join(FRAME_STORAGE_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
    
    capture_thread = threading.Thread(target=capture_frames, args=(capture_rate,))
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

def get_latest_logs():
    global log_content
    return log_content

def analyze_frames_continuous(num_frames, analysis_prompt, capture_rate, analysis_frequency):
    global is_analyzing, analysis_output
    while is_analyzing:
        try:
            captured_frames = get_captured_frames()[:num_frames]
            if captured_frames:
                analysis_results = analyze_video_content(captured_frames, analysis_prompt)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] Analysis results:", analysis_results)
                analysis_output = f"[{timestamp}]\n{analysis_results}\n\n" + analysis_output
                yield analysis_output
            time.sleep(analysis_frequency)
        except Exception as e:
            print(f"Error in analyze_frames_continuous: {e}")
            time.sleep(analysis_frequency)

def update_analysis_output(current_status_textbox, analysis_output):
    current_status_textbox.value = analysis_output

def start_analysis(num_frames, analysis_prompt, capture_rate, analysis_frequency):
    global analysis_thread, is_analyzing, analysis_output
    is_analyzing = True
    analysis_output = ""

    def run_analysis(current_status_textbox):
        for result in analyze_frames_continuous(num_frames, analysis_prompt, capture_rate, analysis_frequency):
            if not is_analyzing:
                break
            update_analysis_output(current_status_textbox, result)

    analysis_thread = threading.Thread(target=run_analysis, args=(current_status_textbox,))
    analysis_thread.daemon = True
    analysis_thread.start()
    return gr.update(value="分析已开始"), gr.update(value="")

def stop_analysis():
    global is_analyzing, analysis_thread
    is_analyzing = False
    if analysis_thread:
        analysis_thread.join()
    return gr.update(value="分析已停止")

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

        with gr.TabItem("视频流审核"):
            gr.Markdown("使用摄像头捕获视频流并截取帧")
            video_stream_output = gr.Image(label="视频流")
            
            capture_rate_input = gr.Slider(minimum=1, maximum=10, step=1, value=1, label="截帧频率 (秒)")
            frames_to_analyze = gr.Slider(minimum=1, maximum=10, step=1, value=3, label="每次分析的帧数", interactive=True)
            analysis_prompt_input = gr.Textbox(label="分析提示词", value=DEFAULT_VIDEO_FRAME_PROMPT, lines=2)
            analysis_frequency = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="分析频率 (秒)", interactive=True)
            
            start_capture_button = gr.Button("开始截帧")
            start_analysis_button = gr.Button("开始分析")
            stop_analysis_button = gr.Button("停止分析")
            stop_capture_button = gr.Button("停止截帧")

            gr.Markdown("分析状态")
            current_status_textbox = gr.Textbox(label="分析状态", lines=1, max_lines=10, autoscroll=False)

            gr.Markdown("已捕获的帧")
            captured_frames_gallery = gr.Gallery(label="已捕获的帧", columns=5, height="auto")

            gr.Markdown("更新已截取帧路径")
            update_path_button = gr.Button("更新已截取帧路径")
            
            captured_frames_output = gr.Textbox(label="已截取帧的保存路径")

            def start_capture(capture_rate):
                global log_content
                log_content = "开始截帧...\n"
                start_capture_thread(capture_rate)
                return gr.update(value="开始截帧"), gr.update(value=log_content)

            def stop_capture():
                stop_capture_thread()
                captured_frames = get_captured_frames()
                return gr.update(value="停止截帧"), gr.update(value=captured_frames)

            start_capture_button.click(fn=start_capture, inputs=[capture_rate_input], outputs=[captured_frames_output])
            start_analysis_button.click(
                fn=start_analysis,
                inputs=[frames_to_analyze, analysis_prompt_input, capture_rate_input, analysis_frequency],
                outputs=[current_status_textbox, captured_frames_output]
            )
            stop_analysis_button.click(fn=stop_analysis, inputs=[], outputs=[current_status_textbox])
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
