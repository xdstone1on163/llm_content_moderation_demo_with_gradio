import gradio as gr
import tempfile
import os
import subprocess
from pathlib import Path
import logging
import time
import json
import boto3
import requests

from asr_tool import call_sagemaker, asr_local_file
from aws_clients import start_transcription_job, get_transcription_job
import uuid
import numpy as np
import wave
from datetime import datetime

from config import BUCKET_NAME, TRANSCRIBE_BUCKET, WHISPER_ENDPOINT_NAME, DEFAULT_TEXT_PROMPT
from text_audit import analyze_text_with_llm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language options
LANGUAGE_OPTIONS = {
    "中文": "zh-CN",
    "英语": "en-US",
    "日语": "ja-JP",
    "韩语": "ko-KR"
}


def save_recorded_audio(audio_data):
    """Save recorded audio data to a WAV file"""
    if not isinstance(audio_data, tuple) or len(audio_data) != 2:
        return None

    sample_rate, audio_array = audio_data

    # 确保数据类型正确
    if not isinstance(audio_array, np.ndarray):
        logger.error("音频数据格式错误")
        return None

    # 添加数据范围检查
    if np.max(np.abs(audio_array)) > 1.0:
        logger.warning("音频数据超出范围，进行归一化")
        audio_array = audio_array / np.max(np.abs(audio_array))

    # 在转换前添加调试信息
    logger.debug(f"Audio array stats: min={np.min(audio_array)}, max={np.max(audio_array)}, dtype={audio_array.dtype}")
    logger.debug(f"Sample rate: {sample_rate}")

    temp_path = os.path.join(tempfile.gettempdir(), f"recorded_audio_{uuid.uuid4()}.wav")

    try:
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(sample_rate))  # 确保采样率为整数

            # 更稳健的转换方式
            audio_array_int = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
            wav_file.writeframes(audio_array_int.tobytes())

        logger.info(f"录音已保存到: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"保存录音失败: {str(e)}")
        return None


def process_uploaded_file(file):
    """Process uploaded audio or video file and extract audio"""
    if file is None:
        return None, "请选择文件"

    try:
        logger.info(f"处理上传的文件: {file.name}")

        # Create output file
        output_path = os.path.join(tempfile.gettempdir(), "processed_audio.wav")

        # Convert to WAV using ffmpeg
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', file.name,  # Input file
            '-vn',  # Disable video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            output_path  # Output file
        ]

        # Run ffmpeg
        result = subprocess.run(command, capture_output=True, text=True)
        result.check_returncode()

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path, "处理成功"
        else:
            return None, "处理失败：输出文件无效"

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return None, f"处理失败：{e.stderr}"
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None, f"处理失败：{str(e)}"


def upload_to_s3(file_path, bucket_name=TRANSCRIBE_BUCKET):
    """Upload file to S3 and return the S3 URI"""
    try:
        s3_client = boto3.client('s3')
        file_name = f"audio/{uuid.uuid4()}.wav"
        s3_client.upload_file(file_path, bucket_name, file_name)
        return f"s3://{bucket_name}/{file_name}"
    except Exception as e:
        logger.error(f"S3上传失败: {str(e)}")
        raise


def transcribe_audio(audio_input, language_choice="英文", asr_type="Transcribe",model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"):
    """Start transcription job for the audio file"""
    if audio_input is None:
        return "请先上传或录制音频", {}

    try:
        # Handle different types of audio input
        if isinstance(audio_input, tuple):
            # This is from the microphone recording
            audio_path = save_recorded_audio(audio_input)
            if audio_path is None:
                return "录音处理失败", {}
        elif isinstance(audio_input, str):
            # This is already a file path
            audio_path = audio_input
        else:
            return "无效的音频输入", {}

        logger.info(f"开始处理音频文件: {audio_path}")

        # print(asr_type)
        if asr_type == "Sagemaker":
            whisper_txt = asr_local_file(WHISPER_ENDPOINT_NAME, audio_path)
            # print("---")
            print(whisper_txt)

            llm_analysis = analyze_text_with_llm(whisper_txt, DEFAULT_TEXT_PROMPT, model_id)


            return (whisper_txt, llm_analysis)
        else:
            # Upload to S3
            s3_uri = upload_to_s3(audio_path)
            logger.info(f"文件已上传到 S3: {s3_uri}")

            # Determine language and toxicity detection strategy
            detect_toxicity = False
            language_code = None

            if language_choice == "英语":
                # For English or auto-detect, enable toxicity detection
                detect_toxicity = True
                language_code = 'en-US'
            else:
                # For other languages, disable toxicity detection
                detect_toxicity = False
                language_code = LANGUAGE_OPTIONS.get(language_choice)

            logger.info(f"语言: {language_code}, 毒性检测: {detect_toxicity}")

            # Start transcription job
            job_name = f"transcribe_{uuid.uuid4()}"
            response = start_transcription_job(job_name, s3_uri, language_code, detect_toxicity)
            logger.info(f"转录任务已启动: {job_name}")

            # Wait for job completion (with timeout)
            timeout = time.time() + 300  # 5 minutes timeout
            while time.time() < timeout:
                job = get_transcription_job(job_name)

                status = job['TranscriptionJob']['TranscriptionJobStatus']
                logger.info(f"转录任务状态: {status}")

                if status == 'COMPLETED':
                    # Get the transcript
                    transcript_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    transcript_response = requests.get(transcript_uri)
                    transcript_data = transcript_response.json()

                    # Extract the text
                    transcript = transcript_data['results']['transcripts'][0]['transcript']

                    # Extract toxicity results
                    toxicity_results = {}
                    if detect_toxicity and 'toxicity_detection' in transcript_data['results']:
                        toxicity_results = {
                            "toxicity_details": transcript_data['results']['toxicity_detection']
                        }
                        logger.warning(f"音频毒性检测结果: {json.dumps(toxicity_results, indent=2)}")

                    # Get detected language
                    detected_lang = job['TranscriptionJob'].get('LanguageCode', '未知')

                    return (
                        f"转录完成 (检测到的语言: {detected_lang})：\n\n{transcript}",
                        toxicity_results
                    )

                elif status == 'FAILED':
                    error = job['TranscriptionJob'].get('FailureReason', '未知错误')
                    return f"转录失败：{error}", {}

                time.sleep(5)  # Wait 5 seconds before checking again

            return "转录超时，请稍后重试", {}

    except Exception as e:
        logger.error(f"转录错误: {str(e)}")
        return f"转录错误：{str(e)}", {}


# Rest of the code remains the same as in the previous implementation
# (Gradio interface creation code is unchanged)
def create_audio_interface(example_audios,model_dropdown):
    """Create the audio interface components"""
    with gr.Blocks() as audio_audit:
        with gr.Row():
            # File upload column
            with gr.Column():
                gr.Markdown("### 上传音频或视频文件")
                file_upload = gr.File(
                    label="点击上传或拖拽文件到此处",
                    file_types=["audio", "video"]
                )
                upload_button = gr.Button("处理上传的文件")
                upload_status = gr.Textbox(label="上传状态", interactive=False)
                upload_player = gr.Audio(
                    label="音频预览",
                    type="filepath",
                    interactive=True,
                    autoplay=False
                )

            # Recording column
            with gr.Column():
                gr.Markdown("### 录制音频")
                recorder = gr.Microphone(
                    label="点击录制按钮开始录音"
                )
                record_status = gr.Textbox(
                    label="录音状态",
                    value="准备录音",
                    interactive=False
                )

        # Transcription section
        with gr.Row():
            gr.Markdown("### 语音转文本")

        with gr.Row():
            with gr.Column():
                # Language selection
                language_choice = gr.Dropdown(
                    choices=list(LANGUAGE_OPTIONS.keys()),
                    value="英语",
                    label="选择语言",
                    info="选择音频的语言类型"
                )

                # Audio source selection
                audio_source = gr.Radio(
                    choices=["上传的文件", "录制的音频", "样例里的音频"],
                    label="选择音频来源",
                    value="上传的文件"
                )

                # Example audio selection (initially hidden)
                example_audio_dropdown = gr.Dropdown(
                    choices=[os.path.basename(path) for path in example_audios],
                    label="选择样例音频",
                    visible=False
                )

                model_choice = gr.Radio(
                    ["Sagemaker", "Transcribe"],
                    label="选择转录模型",
                    value="Sagemaker",
                )

                # Transcribe button
                transcribe_button = gr.Button("开始转录")

                transcribe_result = gr.Textbox(
                    label="转录结果",
                    interactive=False,
                    lines=10
                )
                # Detailed toxicity detection results
                toxicity_result = gr.JSON(
                    label="音频毒性检测结果",
                    visible=True
                )

        # Set up event handlers
        upload_button.click(
            fn=process_uploaded_file,
            inputs=[file_upload],
            outputs=[upload_player, upload_status]
        )

        # For recordings, automatically update status when recording is complete
        recorder.change(
            fn=lambda x: "录音完成" if x is not None else "准备录音",
            inputs=[recorder],
            outputs=[record_status]
        )

        # Show/hide example audio dropdown based on audio source selection
        def update_example_audio_visibility(audio_source):
            return gr.update(visible=(audio_source == "样例里的音频"))

        audio_source.change(
            fn=update_example_audio_visibility,
            inputs=[audio_source],
            outputs=[example_audio_dropdown]
        )

        # Transcribe function that handles all sources
        def transcribe_selected_audio(audio_source, upload_player, recorder, example_audio, language_choice, asr_type,model_id):
            # print(model_dropdown)
            # print(asr_type)
            if audio_source == "上传的文件":
                return transcribe_audio(upload_player, language_choice, asr_type,model_id)
            elif audio_source == "录制的音频":
                return transcribe_audio(recorder, language_choice, asr_type,model_id)
            else:  # 样例里的音频
                example_path = next((path for path in example_audios if os.path.basename(path) == example_audio), None)
                return transcribe_audio(example_path, language_choice, asr_type,model_id) if example_path else (
                "样例音频未找到", {})

        # Transcribe button
        transcribe_button.click(
            fn=transcribe_selected_audio,
            inputs=[
                audio_source,
                upload_player,
                recorder,
                example_audio_dropdown,
                language_choice,
                model_choice,
                model_dropdown
            ],
            outputs=[
                transcribe_result,
                toxicity_result
            ]
        )

    return audio_audit

# The audio interface will be created in main.py
