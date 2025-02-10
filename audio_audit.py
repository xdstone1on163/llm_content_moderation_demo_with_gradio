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
from aws_clients import start_transcription_job, get_transcription_job
import uuid
import numpy as np
import wave
from datetime import datetime
from config import S3_BUCKET_NAME

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language options
LANGUAGE_OPTIONS = {
    "Chinese": "zh-CN",
    "English": "en-US",
    "Japanese": "ja-JP",
    "Korean": "ko-KR"
}

def save_recorded_audio(audio_data):
    """Save recorded audio data to a WAV file"""
    if not isinstance(audio_data, tuple) or len(audio_data) != 2:
        return None
        
    sample_rate, audio_array = audio_data
    
    # Ensure correct data type
    if not isinstance(audio_array, np.ndarray):
        logger.error("Invalid audio data format")
        return None
        
    # Add data range check
    if np.max(np.abs(audio_array)) > 1.0:
        logger.warning("Audio data out of range, normalizing")
        audio_array = audio_array / np.max(np.abs(audio_array))
    
    # Add debug information before conversion
    logger.debug(f"Audio array stats: min={np.min(audio_array)}, max={np.max(audio_array)}, dtype={audio_array.dtype}")
    logger.debug(f"Sample rate: {sample_rate}")
    
    temp_path = os.path.join(tempfile.gettempdir(), f"recorded_audio_{uuid.uuid4()}.wav")
    
    try:
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(int(sample_rate))  # Ensure sample rate is an integer
            
            # More robust conversion method
            audio_array_int = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
            wav_file.writeframes(audio_array_int.tobytes())
            
        logger.info(f"Recording saved to: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Failed to save recording: {str(e)}")
        return None

def process_uploaded_file(file):
    """Process uploaded audio or video file and extract audio"""
    if file is None:
        return None, "Please select a file"
    
    try:
        logger.info(f"Processing uploaded file: {file.name}")
        
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
            return output_path, "Processing successful"
        else:
            return None, "Processing failed: Invalid output file"
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        return None, f"Processing failed: {e.stderr}"
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return None, f"Processing failed: {str(e)}"

def upload_to_s3(file_path):
    """Upload file to S3 and return the S3 URI"""
    try:
        s3_client = boto3.client('s3')
        file_name = f"audio/{uuid.uuid4()}.wav"
        s3_client.upload_file(file_path, S3_BUCKET_NAME, file_name)
        return f"s3://{S3_BUCKET_NAME}/{file_name}"
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise

def transcribe_audio(audio_input, language_choice="English"):
    """Start transcription job for the audio file"""
    if audio_input is None:
        return "Please upload or record audio first", {}
    
    try:
        # Handle different types of audio input
        if isinstance(audio_input, tuple):
            # This is from the microphone recording
            audio_path = save_recorded_audio(audio_input)
            if audio_path is None:
                return "Recording processing failed", {}
        elif isinstance(audio_input, str):
            # This is already a file path
            audio_path = audio_input
        else:
            return "Invalid audio input", {}
            
        logger.info(f"Starting audio file processing: {audio_path}")
        
        # Upload to S3
        s3_uri = upload_to_s3(audio_path)
        logger.info(f"File uploaded to S3: {s3_uri}")
        
        # Determine language and toxicity detection strategy
        detect_toxicity = False
        language_code = None
        
        if language_choice == "English":
            # For English or auto-detect, enable toxicity detection
            detect_toxicity = True
            language_code = 'en-US'
        else:
            # For other languages, disable toxicity detection
            detect_toxicity = False
            language_code = LANGUAGE_OPTIONS.get(language_choice)
        
        logger.info(f"Language: {language_code}, Toxicity Detection: {detect_toxicity}")
        
        # Start transcription job
        job_name = f"transcribe_{uuid.uuid4()}"
        response = start_transcription_job(job_name, s3_uri, language_code, detect_toxicity)
        logger.info(f"Transcription job started: {job_name}")
        
        # Wait for job completion (with timeout)
        timeout = time.time() + 300  # 5 minutes timeout
        while time.time() < timeout:
            job = get_transcription_job(job_name)
            
            status = job['TranscriptionJob']['TranscriptionJobStatus']
            logger.info(f"Transcription job status: {status}")
            
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
                    logger.warning(f"Audio toxicity detection results: {json.dumps(toxicity_results, indent=2)}")
                
                # Get detected language
                detected_lang = job['TranscriptionJob'].get('LanguageCode', 'Unknown')
                
                return (
                    f"Transcription completed (Detected language: {detected_lang}):\n\n{transcript}", 
                    toxicity_results
                )
            
            elif status == 'FAILED':
                error = job['TranscriptionJob'].get('FailureReason', 'Unknown error')
                return f"Transcription failed: {error}", {}
            
            time.sleep(5)  # Wait 5 seconds before checking again
            
        return "Transcription timed out, please try again later", {}
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return f"Transcription error: {str(e)}", {}

def create_audio_interface(example_audios):
    """Create the audio interface components"""
    with gr.Blocks() as audio_audit:
        with gr.Row():
            # File upload column
            with gr.Column():
                gr.Markdown("### Upload Audio or Video File")
                file_upload = gr.File(
                    label="Click to upload or drag and drop file",
                    file_types=["audio", "video"]
                )
                upload_button = gr.Button("Process Uploaded File")
                upload_status = gr.Textbox(label="Upload Status", interactive=False)
                upload_player = gr.Audio(
                    label="Audio Preview",
                    type="filepath",
                    interactive=True,
                    autoplay=False
                )

            # Recording column
            with gr.Column():
                gr.Markdown("### Record Audio")
                recorder = gr.Microphone(
                    label="Click record button to start recording"
                )
                record_status = gr.Textbox(
                    label="Recording Status",
                    value="Ready to record",
                    interactive=False
                )

        # Transcription section
        with gr.Row():
            gr.Markdown("### Speech to Text")
            
        with gr.Row():
            with gr.Column():
                # Language selection
                language_choice = gr.Dropdown(
                    choices=list(LANGUAGE_OPTIONS.keys()),
                    value="English",
                    label="Select Language",
                    info="Choose the language of the audio"
                )
                
                # Audio source selection
                audio_source = gr.Radio(
                    choices=["Uploaded File", "Recorded Audio", "Sample Audio"],
                    label="Select Audio Source",
                    value="Uploaded File"
                )
                
                # Example audio selection (initially hidden)
                example_audio_dropdown = gr.Dropdown(
                    choices=[os.path.basename(path) for path in example_audios],
                    label="Select Sample Audio",
                    visible=False
                )
                
                # Transcribe button
                transcribe_button = gr.Button("Start Transcription")
                
                # Results
                transcribe_result = gr.Textbox(
                    label="Transcription Result",
                    interactive=False,
                    lines=10
                )
                
                # Detailed toxicity detection results
                toxicity_result = gr.JSON(
                    label="Audio Toxicity Detection Results",
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
            fn=lambda x: "Recording complete" if x is not None else "Ready to record",
            inputs=[recorder],
            outputs=[record_status]
        )
        
        # Show/hide example audio dropdown based on audio source selection
        def update_example_audio_visibility(audio_source):
            return gr.update(visible=(audio_source == "Sample Audio"))
        
        audio_source.change(
            fn=update_example_audio_visibility,
            inputs=[audio_source],
            outputs=[example_audio_dropdown]
        )
        
        # Transcribe function that handles all sources
        def transcribe_selected_audio(audio_source, upload_player, recorder, example_audio, language_choice):
            if audio_source == "Uploaded File":
                return transcribe_audio(upload_player, language_choice)
            elif audio_source == "Recorded Audio":
                return transcribe_audio(recorder, language_choice)
            else:  # Sample Audio
                example_path = next((path for path in example_audios if os.path.basename(path) == example_audio), None)
                return transcribe_audio(example_path, language_choice) if example_path else ("Sample audio not found", {})
        
        # Transcribe button
        transcribe_button.click(
            fn=transcribe_selected_audio,
            inputs=[
                audio_source,
                upload_player,
                recorder,
                example_audio_dropdown,
                language_choice
            ],
            outputs=[
                transcribe_result, 
                toxicity_result
            ]
        )

    return audio_audit

# The audio interface will be created in main.py
