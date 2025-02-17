import gradio as gr
from image_audit import process_image
from live_moderation import LiveModerationManager
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
    log_queue.put("Starting analysis...")
    return gr.update(value="Analysis Started"), gr.update(value="Stop Analysis"), gr.update(value="Start Capture"), gr.update(value="Stop Capture")

def stop_analysis():
    global is_analyzing, analysis_thread
    is_analyzing = False
    if analysis_thread:
        analysis_thread.join()
        analysis_thread = None
    log_queue.put("Analysis stopped")
    return gr.update(value="Start Analysis"), gr.update(value="Analysis Stopped"), gr.update(value="Start Capture"), gr.update(value="Stop Capture")

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
    gr.Markdown("## Content Moderation Solution")
    
    with gr.Row():
        # Left column for model selection and price display
        with gr.Column(scale=1):
            with gr.Group():
                gr.Markdown("Select Model")
                model_dropdown = gr.Dropdown(choices=MODEL_LIST, value="anthropic.claude-3-5-sonnet-20241022-v2:0")

            # with gr.Group():
            #     gr.Markdown("Model Price")
            #     model_price_display = gr.Textbox(value="", interactive=False)
            #
            #     def update_model_price(model):
            #         for price_info in MODEL_PRICES:
            #             if price_info["Model"] == model:
            #                 return f"Input price per million tokens: ${price_info['Input Price Per Million Tokens']:.2f}\nOutput price per million tokens: ${price_info['Output Price Per Million Tokens']:.2f}"
            #         return "Price information not available"
            #
            #     model_dropdown.change(fn=update_model_price, inputs=[model_dropdown], outputs=[model_price_display])
        
        # Vertical line separator
        gr.HTML("""
            <div style="width: 2px; height: 100vh; background-color: #e5e5e5; margin: 0 10px;"></div>
        """)
        
        # Main content area
        with gr.Column(scale=5):
            with gr.Tabs() as tabs:

                # Text audit tab
                with gr.TabItem("Text moderation"):
                    text_input = gr.Textbox(label="Input Text to Audit", value=DEFAULT_TEXT_TO_AUDIT, lines=5)
                    text_prompt_input = gr.Textbox(label="Text Audit Prompt", value=DEFAULT_TEXT_PROMPT, lines=5)
                    text_submit_button = gr.Button("Audit Text")
                    llm_text_output = gr.Textbox(label="LLM Analysis Results")

                    with gr.Group() as comprehend_group:
                        gr.Markdown("Comprehend Processing Results")
                        with gr.Row():
                            sentiment_output = gr.Textbox(label="Sentiment Analysis")
                            entities_output = gr.Textbox(label="Entity Recognition")
                            key_phrases_output = gr.Textbox(label="Key Phrases")
                            pii_entities_output = gr.Textbox(label="PII Entities")
                            toxic_content_output = gr.Textbox(label="Toxic Content Detection")

                # Image audit tab
                with gr.TabItem("Image moderation"):
                    gr.Markdown("### Example Images")
                    example_images = get_example_files('pics')
                    with gr.Row():
                        example_gallery = gr.Gallery(
                            value=example_images,
                            label="Click to select example image",
                            columns=3,
                            height=200,
                            interactive=True
                        )
                    
                    image_input = gr.Image(label="Upload Image", type="pil", interactive=True, sources=["upload", "webcam"])

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
                    image_prompt_input = gr.Textbox(label="LLM Image Multi-modal Analysis Custom Prompt", value=DEFAULT_IMAGE_PROMPT, lines=5)
                    llm_output = gr.Textbox(label="LLM Result")
                    
                    with gr.Group() as rekognition_group:
                        gr.Markdown("Rekognition Audit Results")
                        with gr.Row():
                            rekognition_moderation_output = gr.Textbox(label="Moderation Labels")
                            rekognition_labels_output = gr.Textbox(label="Detected Labels")
                            rekognition_faces_output = gr.Textbox(label="Detected Faces")
                    
                    submit_button = gr.Button("Analyze Image")

                # Video frame audit tab
                with gr.TabItem("Static video moderation"):
                    gr.Markdown("### Example Videos")
                    example_videos = get_example_files('videos')
                    with gr.Row():
                        example_gallery_videos = gr.Gallery(
                            value=example_videos,
                            label="Click to select example video",
                            columns=3,
                            height=200,
                            interactive=True
                        )
                    
                    gr.Markdown("Please use the video component below to upload or record a video. Uploaded videos should not exceed 200MB.")
                    video_input = gr.Video(label="Upload or Record Video", sources=["upload"])

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
                    num_frames_input = gr.Slider(minimum=1, maximum=20, step=1, value=5, label="Number of Frames")
                    video_prompt_input = gr.Textbox(label="Video Content Audit Prompt", value=DEFAULT_VIDEO_PROMPT, lines=5)
                    video_output = gr.Gallery(label="Extracted Video Frames", columns=20, height="auto")
                    video_result = gr.Textbox(label="Processing Result")
                    video_analysis = gr.Textbox(label="Video Content Analysis")
                    video_submit_button = gr.Button("Process Video")

                # Video stream audit tab
                with gr.TabItem("Video stream moderation"):
                    gr.Markdown("Use webcam to capture video stream")
                    video_stream_output = gr.Image(label="Capture Video Stream from Webcam", sources=["webcam"])
                    
                    with gr.Row():
                        capture_rate_input = gr.Slider(minimum=1, maximum=10, step=1, value=1, label="Capture Rate (seconds)")
                        start_capture_button = gr.Button("Start Capture")
                    
                    frames_to_analyze = gr.Slider(minimum=1, maximum=10, step=1, value=3, label="Frames to Analyze", interactive=True)
                    analysis_prompt_input = gr.Textbox(label="Analysis Prompt", value=DEFAULT_VIDEO_FRAME_PROMPT, lines=2)
                    analysis_frequency = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="Analysis Frequency (seconds)", interactive=True)
                    
                    start_analysis_button = gr.Button("Start Analysis")
                    stop_analysis_button = gr.Button("Stop Analysis")
                    stop_capture_button = gr.Button("Stop Capture")

                    gr.Markdown("Analysis Status")
                    current_status_html = gr.HTML(value="<div style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>No logs yet...</div>")

                    gr.Markdown("Captured Frames")
                    captured_frames_gallery = gr.Gallery(label="Captured Frames", columns=5, height="auto")
                    captured_frames_output = gr.Textbox(label="Captured Frames Save Path")

                # Audio transcription tab
                with gr.TabItem("Audio moderation"):
                    gr.Markdown("Please use the components below to upload audio/video files, record audio, or select sample audio. Audio can be extracted from video files.")
                    
                    # Get example audio files
                    example_audios = [f for f in get_example_files('audios') if f.endswith('.mp3') or f.endswith('.mp4') or f.endswith('.wav')]
                    
                    # Create the audio interface
                    audio_interface = create_audio_interface(example_audios,model_dropdown)
                    
                    # Function to handle example audio selection
                    def load_example_audio(audio_name):
                        selected_path = next((f for f in example_audios if os.path.basename(f) == audio_name), None)
                        if selected_path and os.path.isfile(selected_path):
                            return (
                                gr.update(value="Sample Audio"),  # audio source radio
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
                        if isinstance(child, gr.Radio) and child.label == "Select Audio Source":
                            audio_source = child
                        elif isinstance(child, gr.Dropdown) and child.label == "Select Sample Audio":
                            example_audio_dropdown = child

                    if audio_source and example_audio_dropdown:
                        # Function to handle audio source selection
                        def update_example_audio_visibility(audio_source_value):
                            return gr.update(visible=(audio_source_value == "Sample Audio"))

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
                                return gr.update(value=selected_path), gr.update(value="Sample Audio")
                            return gr.update(), gr.update()

                        # Connect example audio selection to update the player
                        example_audio_dropdown.change(
                            fn=load_example_audio,
                            inputs=[example_audio_dropdown],
                            outputs=[upload_player, audio_source]
                        )

                with gr.TabItem("Live moderation"):
                    def update_visibility(choices):
                        return gr.update(visible="Face moderation" in choices)

                    def upload_face_image(image):
                        if image is not None:
                            print(image)
                            return image
                        return "No images uploaded"

                    checkbox_group = gr.CheckboxGroup(
                        choices=["Content moderation", "Face moderation"],
                        label="Please select the moderation type",
                        info="You can select one or more"
                    )

                    image_input_live = gr.Image(label="Upload pictures", visible=False)
                    image_input_live.change(fn=upload_face_image, inputs=image_input_live)

                    checkbox_group.change(
                        fn=update_visibility,
                        inputs=[checkbox_group],
                        outputs=[image_input_live]
                    )

                    gr.Markdown("Please enter the video url")

                    with gr.Row():
                        video_url = gr.Textbox(label="Video URL")

                    submit_btn = gr.Button("Submit moderation task")

                    with gr.Row():
                        query_btn = gr.Button("Real-time status query")
                        stop_btn = gr.Button("Stop status query")

                    status_output = gr.HTML(label="Query Result")

                    live_moderation_manager = LiveModerationManager()

                    def submit_video(url, checkbox_groups, image):
                        yield live_moderation_manager.submit_video(url, checkbox_groups, image)

                    def query_status(url):
                        live_moderation_manager.stop_query()
                        yield from live_moderation_manager.query_status(url)

                    submit_btn.click(fn=submit_video, inputs=[video_url, checkbox_group, image_input_live])
                    query_btn.click(fn=query_status, inputs=video_url, outputs=status_output)
                    stop_btn.click(fn=live_moderation_manager.stop_query)

            def start_capture(capture_rate):
                global stop_capture_flag, capture_thread
                
                # Clear the captured frames directory
                if os.path.exists(FRAME_STORAGE_DIR):
                    shutil.rmtree(FRAME_STORAGE_DIR)
                os.makedirs(FRAME_STORAGE_DIR)
                
                log_queue.put("Starting frame capture...")
                stop_capture_flag = threading.Event()
                capture_thread = start_frame_capture(stop_capture_flag)
                return (
                    gr.update(value="Frame Capture Started"),
                    gr.update(value="Start Analysis"),
                    gr.update(value="Stop Analysis"),
                    gr.update(value="Stop Capture"),
                    gr.update(value=os.path.abspath(FRAME_STORAGE_DIR))
                )

            def stop_capture():
                global capture_thread, stop_capture_flag
                if stop_capture_flag is not None:
                    stop_frame_capture(capture_thread, stop_capture_flag)
                    captured_frames = get_captured_frames()
                    capture_thread = None
                    stop_capture_flag = None
                    log_queue.put("Frame capture stopped")
                    return (
                        gr.update(value="Start Capture"),
                        gr.update(value="Start Analysis"),
                        gr.update(value="Stop Analysis"),
                        gr.update(value="Frame Capture Stopped"),
                        gr.update(value=captured_frames)
                    )
                return (
                    gr.update(value="Start Capture"),
                    gr.update(value="Start Analysis"),
                    gr.update(value="Stop Analysis"),
                    gr.update(value="Not Capturing"),
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
