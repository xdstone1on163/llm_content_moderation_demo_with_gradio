import gradio as gr
from image_audit import process_image
from video_audit import process_video, analyze_video_content
from text_audit import process_text
from audio_audit import create_audio_interface
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_IMAGE_PROMPT, DEFAULT_VIDEO_PROMPT, DEFAULT_TEXT_PROMPT, DEFAULT_VIDEO_FRAME_PROMPT, DEFAULT_TEXT_TO_AUDIT, MODEL_LIST, MODEL_PRICES
import cv2
import threading
import time
import os
import glob
import queue
import shutil
import logging
from PIL import Image
from video_stream import (
    start_frame_capture, stop_frame_capture, get_latest_captured_frame_path,
    live_logs_as_html, log_queue
)

# Global variables for video capture
capture_interval = 1  # Capture a frame every 1 second
is_running = False
is_analyzing = False
capture_thread = None
analysis_thread = None
latest_captured_frame_path = None
analysis_output = ""
stop_capture_flag = None  # Global flag to control frame capture
log_history = []  # Store recent logs

# Ensure the directory for storing frames exists
FRAME_STORAGE_DIR = os.path.join(os.getcwd(), 'captured_images')
os.makedirs(FRAME_STORAGE_DIR, exist_ok=True)

def get_captured_frames():
    """
    Get a list of all captured frames, sorted by timestamp (newest first)
    """
    frames = []
    try:
        # Get all jpg files in the directory
        files = glob.glob(os.path.join(FRAME_STORAGE_DIR, "frame_*.jpg"))
        # Sort files by modification time (newest first)
        frames = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
    except Exception as e:
        print(f"Error getting captured frames: {e}")
    return frames

def analyze_frames_continuous(num_frames, analysis_prompt, capture_rate, analysis_frequency, model_id):
    global is_analyzing, analysis_output
    while is_analyzing:
        try:
            captured_frames = get_captured_frames()[:num_frames]
            if captured_frames:
                # Convert frame paths to PIL Images
                frame_images = []
                for frame_path in captured_frames:
                    try:
                        with Image.open(frame_path) as img:
                            frame_images.append(img.copy())
                    except Exception as e:
                        logging.error(f"Error opening image {frame_path}: {str(e)}")
                analysis_results = analyze_video_content(frame_images, analysis_prompt, model_id)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                log_message = f"[{timestamp}] Analysis results: {analysis_results}"
                print(log_message)
                log_queue.put(log_message)
                analysis_output = f"[{timestamp}]\n{analysis_results}\n\n" + analysis_output
            time.sleep(analysis_frequency)
        except Exception as e:
            error_message = f"Error in analyze_frames_continuous: {e}"
            print(error_message)
            log_queue.put(error_message)
            time.sleep(analysis_frequency)

def start_analysis(num_frames, analysis_prompt, capture_rate, analysis_frequency, model_id):
    global analysis_thread, is_analyzing, analysis_output
    is_analyzing = True
    analysis_output = ""

    def run_analysis():
        analyze_frames_continuous(num_frames, analysis_prompt, capture_rate, analysis_frequency, model_id)

    analysis_thread = threading.Thread(target=run_analysis)
    analysis_thread.daemon = True
    analysis_thread.start()
    log_queue.put("开始分析...")
    return gr.update(value="分析已开始"), gr.update(value="停止分析"), gr.update(value="开始截帧"), gr.update(value="停止截帧")

def stop_analysis():
    global is_analyzing, analysis_thread
    is_analyzing = False
    if analysis_thread:
        analysis_thread.join()
        analysis_thread = None
    log_queue.put("停止分析")
    return gr.update(value="开始分析"), gr.update(value="分析已停止"), gr.update(value="开始截帧"), gr.update(value="停止截帧")

def update_log_display():
    global log_history
    new_logs = []
    while not log_queue.empty():
        try:
            log_message = log_queue.get_nowait()
            new_logs.append(log_message)
        except queue.Empty:
            break
    
    log_history = new_logs + log_history
    log_history = log_history[:100]  # Keep only the most recent 100 logs
    
    if log_history:
        log_content = "".join([f"<div class='log-item'>{log}</div>" for log in log_history])
        return gr.update(value=f"""
            <div id='log-container' style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>
                <style>
                    #log-container {{
                        display: flex;
                        flex-direction: column;
                    }}
                    .log-item {{
                        text-align: left;
                        width: 100%;
                    }}
                </style>
                {log_content}
                <script>
                    var logContainer = document.getElementById('log-container');
                    logContainer.scrollTop = 0;
                </script>
            </div>
        """)
    return gr.update()

def continuous_update():
    while True:
        time.sleep(1)  # Update every second
        yield update_log_display()

def get_example_files(directory):
    """Get list of files from examples directory"""
    example_dir = os.path.join('examples', directory)
    if os.path.exists(example_dir):
        return sorted([os.path.join(example_dir, f) for f in os.listdir(example_dir) if not f.startswith('.')])
    return []

with gr.Blocks() as demo:
    gr.Markdown("## 内容审核 Demo")
    
    with gr.Row():
        # Left column for model selection and price display
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("选择模型")
                model_dropdown = gr.Dropdown(choices=MODEL_LIST, value="anthropic.claude-3-5-sonnet-20241022-v2:0")

            with gr.Group():
                gr.Markdown("模型价格")
                model_price_display = gr.Textbox(value="", interactive=False)

                def update_model_price(model):
                    for price_info in MODEL_PRICES:
                        if price_info["模型"] == model:
                            return f"输入每百万token价格: ${price_info['输入每百万token价格']:.2f}\n输出每百万token价格: ${price_info['输出每百万token价格']:.2f}"
                    return "价格信息不可用"

                model_dropdown.change(fn=update_model_price, inputs=[model_dropdown], outputs=[model_price_display])
        
        # Vertical line separator
        gr.HTML("""
            <div style="width: 2px; height: 100vh; background-color: #e5e5e5; margin: 0 10px;"></div>
        """)
        
        # Main content area
        with gr.Column(scale=4):
            with gr.Tabs() as tabs:
                # Image audit tab
                with gr.TabItem("图片审核"):
                    gr.Markdown("### 示例图片")
                    example_images = get_example_files('pics')
                    with gr.Row():
                        example_gallery = gr.Gallery(
                            value=example_images,
                            label="点击选择示例图片",
                            columns=3,
                            height=200,
                            interactive=True
                        )
                    
                    image_input = gr.Image(label="上传图片", type="pil", interactive=True, sources=["upload", "webcam"])

                    def load_example_image(evt: gr.SelectData, gallery):
                        try:
                            selected_path = example_images[evt.index]
                            if os.path.isfile(selected_path):
                                return Image.open(selected_path)
                            else:
                                print(f"File not found: {selected_path}")
                                return None
                        except Exception as e:
                            print(f"Error loading image: {e}")
                            return None

                    example_gallery.select(load_example_image, example_gallery, image_input)
                    image_prompt_input = gr.Textbox(label="LLM图片多模态分析自定义提示词", value=DEFAULT_IMAGE_PROMPT, lines=5)
                    llm_output = gr.Textbox(label="LLM 结果")
                    
                    with gr.Group() as rekognition_group:
                        gr.Markdown("Rekognition审核结果")
                        with gr.Row():
                            rekognition_moderation_output = gr.Textbox(label="审核标签")
                            rekognition_labels_output = gr.Textbox(label="检测标签")
                            rekognition_faces_output = gr.Textbox(label="检测人脸")
                    
                    submit_button = gr.Button("分析图片")

                # Video frame audit tab
                with gr.TabItem("静态视频审核"):
                    gr.Markdown("### 示例视频")
                    example_videos = get_example_files('videos')
                    with gr.Row():
                        example_gallery_videos = gr.Gallery(
                            value=example_videos,
                            label="点击选择示例视频",
                            columns=3,
                            height=200,
                            interactive=True
                        )
                    
                    gr.Markdown("请使用下面的视频组件上传视频文件或录制视频。上传的视频不要超过200MB。")
                    video_input = gr.Video(label="上传或录制视频")

                    def load_example_video(evt: gr.SelectData, gallery):
                        try:
                            selected_path = example_videos[evt.index]
                            if os.path.isfile(selected_path):
                                return selected_path
                            else:
                                print(f"File not found: {selected_path}")
                                return None
                        except Exception as e:
                            print(f"Error loading video: {e}")
                            return None

                    example_gallery_videos.select(load_example_video, example_gallery_videos, video_input)
                    num_frames_input = gr.Slider(minimum=1, maximum=20, step=1, value=5, label="抽取帧数")
                    video_prompt_input = gr.Textbox(label="视频内容审核提示词", value=DEFAULT_VIDEO_PROMPT, lines=5)
                    video_output = gr.Gallery(label="抽取的视频帧", columns=20, height="auto")
                    video_result = gr.Textbox(label="处理结果")
                    video_analysis = gr.Textbox(label="视频内容分析")
                    video_submit_button = gr.Button("处理视频")

                # Video stream audit tab
                with gr.TabItem("视频流审核"):
                    gr.Markdown("使用摄像头捕获视频流")
                    video_stream_output = gr.Image(label="从摄像头捕获视频流",sources=["webcam"])
                    
                    with gr.Row():
                        capture_rate_input = gr.Slider(minimum=1, maximum=10, step=1, value=1, label="截帧频率 (秒)")
                        start_capture_button = gr.Button("开始截帧")
                    
                    frames_to_analyze = gr.Slider(minimum=1, maximum=10, step=1, value=3, label="每次分析的帧数", interactive=True)
                    analysis_prompt_input = gr.Textbox(label="分析提示词", value=DEFAULT_VIDEO_FRAME_PROMPT, lines=2)
                    analysis_frequency = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="分析频率 (秒)", interactive=True)
                    
                    start_analysis_button = gr.Button("开始分析")
                    stop_analysis_button = gr.Button("停止分析")
                    stop_capture_button = gr.Button("停止截帧")

                    gr.Markdown("分析状态")
                    current_status_html = gr.HTML(value="<div style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>No logs yet...</div>")

                    gr.Markdown("已捕获的帧")
                    captured_frames_gallery = gr.Gallery(label="已捕获的帧", columns=5, height="auto")
                    captured_frames_output = gr.Textbox(label="已截取帧的保存路径")

                # Audio transcription tab
                with gr.TabItem("音视频转录"):
                    gr.Markdown("请使用下面的组件上传音频/视频文件、录制音频或选择样例音频。支持从视频文件中提取音频。")
                    
                    # Get example audio files
                    example_audios = [f for f in get_example_files('audios') if f.endswith('.mp3') or f.endswith('.mp4') or f.endswith('.wav')]
                    
                    # Create the audio interface
                    audio_interface = create_audio_interface(example_audios)
                    
                    # Function to handle example audio selection
                    def load_example_audio(audio_name):
                        selected_path = next((f for f in example_audios if os.path.basename(f) == audio_name), None)
                        if selected_path and os.path.isfile(selected_path):
                            return (
                                gr.update(value="样例音频"),  # audio source radio
                                gr.update(value=audio_name),  # example audio dropdown
                                gr.update(value=selected_path)  # audio preview (upload_player)
                            )
                        else:
                            print(f"File not found: {audio_name}")
                            return gr.update(), gr.update(), gr.update()

                    # Find the components we need
                    upload_player = audio_interface.children[0].children[0].children[3]  # audio preview
                    audio_source = None
                    example_audio_dropdown = None
                    for child in audio_interface.children[2].children[0].children:
                        if isinstance(child, gr.Radio) and child.label == "选择音频来源":
                            audio_source = child
                        elif isinstance(child, gr.Dropdown) and child.label == "选择样例音频":
                            example_audio_dropdown = child

                    if audio_source and example_audio_dropdown:
                        # Function to handle audio source selection
                        def update_example_audio_visibility(audio_source_value):
                            return gr.update(visible=(audio_source_value == "样例音频"))

                        audio_source.change(
                            fn=update_example_audio_visibility,
                            inputs=[audio_source],
                            outputs=[example_audio_dropdown]
                        )

                        # Function to handle example audio selection
                        def load_example_audio(example_name):
                            if not example_name:
                                return gr.update()
                            selected_path = next((f for f in example_audios if os.path.basename(f) == example_name), None)
                            if selected_path and os.path.isfile(selected_path):
                                return gr.update(value=selected_path), gr.update(value="样例音频")
                            return gr.update(), gr.update()

                        # Connect example audio selection to update the player
                        example_audio_dropdown.change(
                            fn=load_example_audio,
                            inputs=[example_audio_dropdown],
                            outputs=[upload_player, audio_source]
                        )

                # Text audit tab
                with gr.TabItem("文本审核"):
                    text_input = gr.Textbox(label="输入待审核文本", value=DEFAULT_TEXT_TO_AUDIT, lines=5)
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

            def start_capture(capture_rate):
                global stop_capture_flag, capture_thread
                
                # Clear the captured frames directory
                if os.path.exists(FRAME_STORAGE_DIR):
                    shutil.rmtree(FRAME_STORAGE_DIR)
                os.makedirs(FRAME_STORAGE_DIR)
                
                log_queue.put("开始截帧...")
                stop_capture_flag = threading.Event()
                capture_thread = start_frame_capture(stop_capture_flag)
                return (
                    gr.update(value="截帧已开始"),
                    gr.update(value="开始分析"),
                    gr.update(value="停止分析"),
                    gr.update(value="停止截帧"),
                    gr.update(value=os.path.abspath(FRAME_STORAGE_DIR))
                )

            def stop_capture():
                global capture_thread, stop_capture_flag
                if stop_capture_flag is not None:
                    stop_frame_capture(capture_thread, stop_capture_flag)
                    captured_frames = get_captured_frames()
                    capture_thread = None
                    stop_capture_flag = None
                    log_queue.put("停止截帧")
                    return (
                        gr.update(value="开始截帧"),
                        gr.update(value="开始分析"),
                        gr.update(value="停止分析"),
                        gr.update(value="截帧已停止"),
                        gr.update(value=captured_frames)
                    )
                return (
                    gr.update(value="开始截帧"),
                    gr.update(value="开始分析"),
                    gr.update(value="停止分析"),
                    gr.update(value="未在截帧"),
                    gr.update(value=[])
                )

            start_capture_button.click(
                fn=start_capture,
                inputs=[capture_rate_input],
                outputs=[start_capture_button, start_analysis_button, stop_analysis_button, stop_capture_button, captured_frames_output]
            )
            start_analysis_button.click(
                fn=start_analysis,
                inputs=[frames_to_analyze, analysis_prompt_input, capture_rate_input, analysis_frequency, model_dropdown],
                outputs=[start_analysis_button, stop_analysis_button, start_capture_button, stop_capture_button]
            )
            stop_analysis_button.click(
                fn=stop_analysis,
                inputs=[],
                outputs=[start_analysis_button, stop_analysis_button, start_capture_button, stop_capture_button]
            )
            stop_capture_button.click(
                fn=stop_capture,
                inputs=[],
                outputs=[start_capture_button, start_analysis_button, stop_analysis_button, stop_capture_button, captured_frames_gallery]
            )

            # Continuous updates
            demo.load(continuous_update, inputs=None, outputs=[current_status_html])

            def process_image_wrapper(image, prompt, model):
                # Process the image and get results
                llm_res, moderation_result, labels_result, faces_result = process_image(image, prompt, model)
                # Return the original image along with results
                return image, llm_res, moderation_result, labels_result, faces_result

            submit_button.click(
                fn=process_image_wrapper,
                inputs=[image_input, image_prompt_input, model_dropdown],
                outputs=[image_input, llm_output, 
                         rekognition_moderation_output, 
                         rekognition_labels_output, 
                         rekognition_faces_output]
            )

            video_submit_button.click(
                fn=process_video,
                inputs=[video_input, num_frames_input, video_prompt_input, model_dropdown],
                outputs=[video_output, video_result, video_analysis]
            )

            text_submit_button.click(
                fn=process_text,
                inputs=[text_input, text_prompt_input, model_dropdown],
                outputs=[llm_text_output, 
                         sentiment_output, entities_output, 
                         key_phrases_output, pii_entities_output, 
                         toxic_content_output]
            )

demo.queue()
demo.launch(share=True)
