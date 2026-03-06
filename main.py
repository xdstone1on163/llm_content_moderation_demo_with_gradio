import gradio as gr
from image_audit import process_image
from video_audit import process_video, analyze_video_content
from video_rekognition import run_video_moderation
from text_audit import process_text
from audio_audit import create_audio_interface
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_IMAGE_PROMPT, DEFAULT_VIDEO_PROMPT, DEFAULT_TEXT_PROMPT, DEFAULT_VIDEO_FRAME_PROMPT, DEFAULT_TEXT_TO_AUDIT, MODEL_LIST, MODEL_PRICES
import concurrent.futures
import threading
import time
import os
import queue
import logging
from PIL import Image
from video_stream import (
    process_streaming_frame, get_captured_frames, clear_captured_frames,
    reset_frame_count, get_frame_count
)

# Global variables for video stream analysis
is_analyzing = False
analysis_thread = None
analysis_output = ""
log_queue = queue.Queue()
log_history = []  # Store recent logs

def analyze_frames_continuous(num_frames, analysis_prompt, analysis_frequency, model_id):
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

def start_analysis(num_frames, analysis_prompt, analysis_frequency, model_id):
    global analysis_thread, is_analyzing, analysis_output
    is_analyzing = True
    analysis_output = ""

    def run_analysis():
        analyze_frames_continuous(num_frames, analysis_prompt, analysis_frequency, model_id)

    analysis_thread = threading.Thread(target=run_analysis)
    analysis_thread.daemon = True
    analysis_thread.start()
    log_queue.put("Analysis started...")
    return gr.update(value="Analysis started"), gr.update(value="Stop Analysis")

def stop_analysis():
    global is_analyzing, analysis_thread
    is_analyzing = False
    if analysis_thread:
        analysis_thread.join()
        analysis_thread = None
    log_queue.put("Analysis stopped")
    return gr.update(value="Start Analysis"), gr.update(value="Analysis stopped")

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

def capture_status_text_value():
    """Return current capture status string."""
    count = get_frame_count()
    if count > 0:
        return f"{count} frame(s) saved"
    return "Waiting for Record..."

def continuous_update():
    while True:
        time.sleep(1)
        yield update_log_display()

def capture_status_update():
    while True:
        time.sleep(1)
        yield capture_status_text_value()

def get_example_files(directory):
    """Get list of files from examples directory"""
    example_dir = os.path.join('examples', directory)
    if os.path.exists(example_dir):
        return sorted([os.path.join(example_dir, f) for f in os.listdir(example_dir) if not f.startswith('.')])
    return []

with gr.Blocks() as demo:
    gr.Markdown("## Content Moderation Demo")
    
    with gr.Row():
        # Left column for model selection and price display
        with gr.Column(scale=1):
            with gr.Group():
                model_dropdown = gr.Dropdown(choices=MODEL_LIST, value="global.anthropic.claude-sonnet-4-6", label="Select Model")
                model_price_display = gr.Textbox(value="", interactive=False, label="Model Price")

                def update_model_price(model):
                    for price_info in MODEL_PRICES:
                        if price_info["model"] == model:
                            return "Input price per million tokens: ${:.2f}\nOutput price per million tokens: ${:.2f}".format(
                                price_info['input_price_per_million'], price_info['output_price_per_million'])
                    return "Price information not available"

                model_dropdown.change(fn=update_model_price, inputs=[model_dropdown], outputs=[model_price_display])
                
                # Set initial price for the default model
                default_model = "global.anthropic.claude-sonnet-4-6"
                demo.load(fn=lambda: update_model_price(default_model), inputs=None, outputs=[model_price_display])
        
        # Vertical line separator
        gr.HTML("""
            <div style="width: 2px; height: 100vh; background-color: #e5e5e5; margin: 0 10px;"></div>
        """)
        
        # Main content area
        with gr.Column(scale=4):
            with gr.Tabs() as tabs:
                # Image audit tab
                with gr.TabItem("Image Audit"):
                    gr.Markdown("### Example Images")
                    example_images = get_example_files('pics')
                    with gr.Row():
                        example_gallery = gr.Gallery(
                            value=example_images,
                            label="Click to select an example image",
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
                    image_prompt_input = gr.Textbox(label="LLM Image Multimodal Analysis Custom Prompt", value=DEFAULT_IMAGE_PROMPT, lines=5)
                    llm_output = gr.Textbox(label="LLM Result")

                    with gr.Group() as rekognition_group:
                        gr.Markdown("Rekognition Audit Results")
                        with gr.Row():
                            rekognition_moderation_output = gr.Textbox(label="Moderation Labels")
                            rekognition_labels_output = gr.Textbox(label="Detection Labels")
                            rekognition_faces_output = gr.Textbox(label="Detected Faces")

                    with gr.Row():
                        image_llm_time = gr.Textbox(label="LLM Processing Time", interactive=False)
                        image_rek_time = gr.Textbox(label="Rekognition Processing Time", interactive=False)

                    submit_button = gr.Button("Analyze Image")

                # Video frame audit tab
                with gr.TabItem("Static Video Audit"):
                    gr.Markdown("### Example Videos")
                    example_videos = get_example_files('videos')
                    with gr.Row():
                        example_gallery_videos = gr.Gallery(
                            value=example_videos,
                            label="Click to select an example video",
                            columns=3,
                            height=200,
                            interactive=True
                        )
                    
                    gr.Markdown("Please use the video component below to upload a video file or record a video. The uploaded video should not exceed 200MB. Alternatively, you can specify an S3 path for a video.")
                    
                    # Video source selection
                    video_source = gr.Radio(
                        choices=["Upload Video", "S3 Path"],
                        value="Upload Video",
                        label="Video Source",
                        interactive=True
                    )
                    
                    # Video upload component
                    video_input = gr.Video(label="Upload or Record Video")
                    
                    # S3 path input
                    s3_path_input = gr.Textbox(
                        label="S3 Video Path (format: s3://bucket-name/path/to/video.mp4)",
                        placeholder="s3://my-bucket/videos/example.mp4",
                        visible=False,
                        info="Note: The model will access the video directly from S3. Make sure your AWS account has access to this S3 bucket and the video is in MP4 format."
                    )

                    with gr.Row():
                        analysis_method = gr.Radio(
                            choices=["Process Video with Frames", "Understand Video Directly"],
                            value="Process Video with Frames",
                            label="Analysis Method",
                            interactive=True
                        )
                        
                    # Add specific model selection for direct video understanding
                    nova_models = ["global.amazon.nova-lite-v1:0", "global.amazon.nova-pro-v1:0", "global.amazon.nova-premier-v1:0", "global.amazon.nova-2-lite-v1:0"]  # Nova models that support video
                    direct_video_model = gr.Dropdown(
                        choices=nova_models,
                        value=nova_models[0],
                        label="Select Nova Model (for direct video understanding)",
                        visible=False  # Initially hidden since default is frame-based
                    )

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
                    
                    # Add frame slider with conditional visibility
                    num_frames_input = gr.Slider(
                        minimum=1, 
                        maximum=20, 
                        step=1, 
                        value=5, 
                        label="Number of frames to extract",
                        visible=True  # Initially visible since default is frame-based
                    )
                    
                    video_prompt_input = gr.Textbox(label="Video Content Audit Prompt", value=DEFAULT_VIDEO_PROMPT, lines=5)
                    
                    with gr.Column(visible=True) as frame_based_components:
                        video_output = gr.Gallery(
                            label="Extracted Video Frames", 
                            columns=20, 
                            height="auto"
                        )
                    
                    video_result = gr.Textbox(label="Processing Result")
                    video_analysis = gr.Textbox(label="Video Content Analysis")

                    with gr.Group():
                        gr.Markdown("Rekognition Video Content Moderation Results")
                        rekognition_video_output = gr.Textbox(
                            label="Rekognition Video Moderation Labels", lines=10, interactive=False
                        )

                    with gr.Row():
                        video_llm_time = gr.Textbox(label="LLM Processing Time", interactive=False)
                        video_rek_time = gr.Textbox(label="Rekognition Processing Time", interactive=False)

                    video_submit_button = gr.Button("Process Video")

                    def update_component_visibility(method):
                        is_frame_based = (method == "Process Video with Frames")
                        return [
                            gr.update(visible=is_frame_based),  # frame slider
                            gr.update(visible=not is_frame_based),  # nova model dropdown
                            gr.update(visible=is_frame_based),  # general model dropdown
                            gr.update(value=""),  # clear processing result
                            gr.update(value=""),  # clear video analysis
                            gr.update(visible=is_frame_based),  # frame based components
                            gr.update(value=""),  # clear rekognition output
                            gr.update(value=""),  # clear llm time
                            gr.update(value=""),  # clear rek time
                        ]
                    
                    def update_video_source_ui(source):
                        if source == "Upload Video":
                            return [
                                gr.update(visible=True, interactive=True),  # video_input
                                gr.update(visible=False),  # s3_path_input
                                gr.update(visible=True, interactive=True),  # analysis_method
                                gr.update(visible=True),  # num_frames_input (conditional visibility)
                                gr.update(visible=False)   # direct_video_model (conditional visibility)
                            ]
                        else:  # S3 Path
                            return [
                                gr.update(visible=False, interactive=False),  # video_input
                                gr.update(visible=True),  # s3_path_input
                                gr.update(visible=True, interactive=False, value="Understand Video Directly"),  # analysis_method
                                gr.update(visible=False),  # num_frames_input
                                gr.update(visible=True)    # direct_video_model
                            ]
                    
                    analysis_method.change(
                        fn=update_component_visibility,
                        inputs=[analysis_method],
                        outputs=[num_frames_input, direct_video_model, model_dropdown,
                                video_result, video_analysis, frame_based_components,
                                rekognition_video_output, video_llm_time, video_rek_time]
                    )
                    
                    video_source.change(
                        fn=update_video_source_ui,
                        inputs=[video_source],
                        outputs=[video_input, s3_path_input, analysis_method, num_frames_input, direct_video_model]
                    )

                # Video stream audit tab
                with gr.TabItem("Video Stream Audit"):
                    gr.Markdown("Use camera to capture video stream. **Click the Record button on the camera to start streaming.**")
                    webcam_input = gr.Image(sources="webcam", streaming=True, label="Camera Feed")

                    with gr.Row():
                        refresh_frames_btn = gr.Button("Refresh Frames")
                        clear_frames_btn = gr.Button("Clear Frames")

                    capture_status_text = gr.Textbox(label="Capture Status", value="Waiting for Record...", interactive=False)
                    capture_rate_input = gr.Slider(minimum=1, maximum=10, step=1, value=1, label="Frame capture rate (seconds)")
                    frames_to_analyze = gr.Slider(minimum=1, maximum=10, step=1, value=3, label="Number of frames to analyze each time", interactive=True)
                    analysis_prompt_input = gr.Textbox(label="Analysis prompt", value=DEFAULT_VIDEO_FRAME_PROMPT, lines=2)
                    analysis_frequency = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="Analysis frequency (seconds)", interactive=True)

                    start_analysis_button = gr.Button("Start Analysis")
                    stop_analysis_button = gr.Button("Stop Analysis")

                    gr.Markdown("Analysis Status")
                    current_status_html = gr.HTML(value="<div style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>No logs yet...</div>")
                    clear_analysis_btn = gr.Button("Clear Analysis Results")

                    gr.Markdown("Captured Frames")
                    captured_frames_gallery = gr.Gallery(label="Captured Frames", columns=5, height="auto")

                # Text audit tab
                with gr.TabItem("Text Audit"):
                    text_input = gr.Textbox(label="Input text for audit", value=DEFAULT_TEXT_TO_AUDIT, lines=5)
                    text_prompt_input = gr.Textbox(label="Text audit prompt", value=DEFAULT_TEXT_PROMPT, lines=5)
                    text_submit_button = gr.Button("Audit Text")
                    llm_text_output = gr.Textbox(label="Large Language Model Analysis Result")
                    
                    with gr.Group() as comprehend_group:
                        gr.Markdown("Comprehend Processing Results")
                        with gr.Row():
                            sentiment_output = gr.Textbox(label="Sentiment Analysis")
                            entities_output = gr.Textbox(label="Entity Recognition")
                            key_phrases_output = gr.Textbox(label="Key Phrases")
                            pii_entities_output = gr.Textbox(label="Personal Sensitive Information")
                            toxic_content_output = gr.Textbox(label="Harmful Content Detection")

                    with gr.Row():
                        text_llm_time = gr.Textbox(label="LLM Processing Time", interactive=False)
                        text_comprehend_time = gr.Textbox(label="Comprehend Processing Time", interactive=False)

                # Audio transcription tab
                with gr.TabItem("Audio/Video Transcription"):
                    gr.Markdown("Please use the component below to upload an audio/video file, record audio, or select a sample audio. Audio extraction from video files is supported.")
                    
                    # Get example audio files
                    example_audios = [f for f in get_example_files('audios') if f.endswith('.mp3') or f.endswith('.mp4') or f.endswith('.wav')]
                    
                    # Create the audio interface
                    audio_interface = create_audio_interface(example_audios)

            def on_stream_frame(frame, capture_rate):
                return process_streaming_frame(frame, capture_rate)

            webcam_input.stream(
                on_stream_frame,
                [webcam_input, capture_rate_input],
                webcam_input,
                time_limit=3600,
                stream_every=0.5,
                concurrency_limit=30,
            )

            def on_refresh_frames():
                return gr.update(value=get_captured_frames())

            refresh_frames_btn.click(
                fn=on_refresh_frames,
                inputs=[],
                outputs=[captured_frames_gallery]
            )

            def on_clear_frames():
                reset_frame_count()
                clear_captured_frames()
                return gr.update(value=[])

            clear_frames_btn.click(
                fn=on_clear_frames,
                inputs=[],
                outputs=[captured_frames_gallery]
            )

            def on_clear_analysis():
                global log_history, analysis_output
                log_history = []
                analysis_output = ""
                while not log_queue.empty():
                    try:
                        log_queue.get_nowait()
                    except queue.Empty:
                        break
                return gr.update(value="<div style='height:300px; overflow-y:auto; font-family:monospace; white-space:pre-wrap;'>No logs yet...</div>")

            clear_analysis_btn.click(
                fn=on_clear_analysis,
                inputs=[],
                outputs=[current_status_html]
            )

            start_analysis_button.click(
                fn=start_analysis,
                inputs=[frames_to_analyze, analysis_prompt_input, analysis_frequency, model_dropdown],
                outputs=[start_analysis_button, stop_analysis_button]
            )
            stop_analysis_button.click(
                fn=stop_analysis,
                inputs=[],
                outputs=[start_analysis_button, stop_analysis_button]
            )

            # Continuous updates
            demo.load(continuous_update, inputs=None, outputs=[current_status_html])
            demo.load(capture_status_update, inputs=None, outputs=[capture_status_text])

            def process_image_wrapper(image, prompt, model):
                llm_res, moderation_result, labels_result, faces_result, llm_elapsed, rek_elapsed = process_image(image, prompt, model)
                return (image, llm_res, moderation_result, labels_result, faces_result,
                        f"{llm_elapsed:.2f}s", f"{rek_elapsed:.2f}s")

            submit_button.click(
                fn=process_image_wrapper,
                inputs=[image_input, image_prompt_input, model_dropdown],
                outputs=[image_input, llm_output,
                         rekognition_moderation_output,
                         rekognition_labels_output,
                         rekognition_faces_output,
                         image_llm_time, image_rek_time]
            )

            def process_video_wrapper(video, s3_path, num_frames, prompt, general_model, nova_model, method, source):
                try:
                    selected_model = nova_model if method == "Understand Video Directly" else general_model
                    analysis_method = "direct" if method == "Understand Video Directly" else "frame"

                    video_path = None
                    is_s3_path = False

                    if source == "S3 Path":
                        video_path = s3_path
                        is_s3_path = True
                        analysis_method = "direct"
                        selected_model = nova_model
                        logging.info(f"Using S3 path: {video_path}")
                    elif isinstance(video, str):
                        video_path = video
                    elif video is not None:
                        video_path = video.name if hasattr(video, 'name') else None

                    if video_path is None:
                        return None, "No video file provided", None, "", "", ""

                    if not is_s3_path and analysis_method == "direct":
                        file_size = os.path.getsize(video_path)
                        max_size = 25 * 1024 * 1024
                        logging.info(f"Video file size: {file_size / (1024 * 1024):.2f} MB")
                        if file_size > max_size:
                            error_msg = f"Video file size ({file_size / (1024 * 1024):.2f} MB) exceeds the maximum allowed size (25 MB) for direct video understanding. Please use a smaller video file or try the frame-based analysis method."
                            logging.error(error_msg)
                            return None, error_msg, None, "", "", ""

                    def timed_llm():
                        start = time.time()
                        result = process_video(video_path, num_frames, prompt, selected_model, analysis_method, is_s3_path)
                        return result, time.time() - start

                    def timed_rek():
                        start = time.time()
                        result = run_video_moderation(video_path, is_s3_path)
                        return result, time.time() - start

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        llm_future = executor.submit(timed_llm)
                        rek_future = executor.submit(timed_rek)

                        (frames, result_msg, analysis), llm_elapsed = llm_future.result()

                        try:
                            rekognition_result, rek_elapsed = rek_future.result()
                        except Exception as e:
                            logging.error(f"Rekognition video moderation error: {e}")
                            rekognition_result = f"=== Rekognition Video Content Moderation ===\nError: {e}"
                            rek_elapsed = 0.0

                    llm_time_str = f"{llm_elapsed:.2f}s"
                    rek_time_str = f"{rek_elapsed:.2f}s"

                    if analysis_method == "direct":
                        return None, result_msg, analysis, rekognition_result, llm_time_str, rek_time_str
                    return frames, result_msg, analysis, rekognition_result, llm_time_str, rek_time_str

                except Exception as e:
                    logging.error(f"Error in process_video_wrapper: {str(e)}")
                    return None, f"Error processing video: {str(e)}", None, "", "", ""

            video_submit_button.click(
                fn=process_video_wrapper,
                inputs=[video_input, s3_path_input, num_frames_input, video_prompt_input, model_dropdown, direct_video_model, analysis_method, video_source],
                outputs=[video_output, video_result, video_analysis, rekognition_video_output, video_llm_time, video_rek_time]
            )

            def process_text_wrapper(text, prompt, model):
                results = process_text(text, prompt, model)
                llm_analysis, sentiment, entities, key_phrases, pii_entities, toxic_content, llm_elapsed, comprehend_elapsed = results
                return (llm_analysis, sentiment, entities, key_phrases, pii_entities, toxic_content,
                        f"{llm_elapsed:.2f}s", f"{comprehend_elapsed:.2f}s")

            text_submit_button.click(
                fn=process_text_wrapper,
                inputs=[text_input, text_prompt_input, model_dropdown],
                outputs=[llm_text_output,
                         sentiment_output, entities_output,
                         key_phrases_output, pii_entities_output,
                         toxic_content_output,
                         text_llm_time, text_comprehend_time]
            )

demo.queue(default_concurrency_limit=5)
demo.launch(share=True)
