import gradio as gr
from image_audit import process_image
from video_audit import process_video
from text_audit import process_text
from audio_audit import create_audio_interface
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_VIDEO_PROMPT, DEFAULT_TEXT_PROMPT

with gr.Blocks() as demo:
    gr.Markdown("## 内容审核 Demo")
    
    with gr.Tabs() as tabs:
        with gr.TabItem("图片审核"):
            image_input = gr.Image(type="pil", label="上传图片", interactive=True)
            system_prompt_input = gr.Textbox(label="LLM图片多模态分析自定义系统提示词", value=DEFAULT_SYSTEM_PROMPT, lines=5)
            llm_output = gr.Textbox(label="LLM 结果")
            with gr.Row():
                rekognition_moderation_output = gr.Textbox(label="Rekognition Moderation Labels")
                rekognition_labels_output = gr.Textbox(label="Rekognition Detected Labels")
                rekognition_faces_output = gr.Textbox(label="Rekognition Detected Faces")
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

        with gr.TabItem("音视频转录"):
            gr.Markdown("请使用下面的组件上传音频/视频文件或录制音频。支持从视频文件中提取音频。")
            audio_components = create_audio_interface()

        with gr.TabItem("文本审核"):
            text_input = gr.Textbox(label="输入待审核文本", lines=5)
            text_prompt_input = gr.Textbox(label="文本审核提示词", value=DEFAULT_TEXT_PROMPT, lines=5)
            text_submit_button = gr.Button("审核文本")
            llm_text_output = gr.Textbox(label="大模型分析结果")
            comprehend_output = gr.Textbox(label="AWS Comprehend 分析结果")

    submit_button.click(
        fn=process_image,
        inputs=[image_input, system_prompt_input],
        outputs=[llm_output, rekognition_moderation_output, rekognition_labels_output, rekognition_faces_output]
    )

    video_submit_button.click(
        fn=process_video,
        inputs=[video_input, num_frames_input, video_prompt_input],
        outputs=[video_output, video_result, video_analysis]
    )

    text_submit_button.click(
        fn=process_text,
        inputs=[text_input, text_prompt_input],
        outputs=[llm_text_output, comprehend_output]
    )

demo.launch(share=True)
