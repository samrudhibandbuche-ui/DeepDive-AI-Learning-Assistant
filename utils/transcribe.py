from pathlib import Path
import whisper
import streamlit as st


@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")


def transcribe_audio(audio_path: str):
    """Convert audio into text using OpenAI Whisper."""

    model = load_whisper_model()

    result = model.transcribe(audio_path)

    transcript = result["text"].strip()

    transcript_folder = Path("transcripts")
    transcript_folder.mkdir(exist_ok=True)

    transcript_file = transcript_folder / f"{Path(audio_path).stem}.txt"

    with open(transcript_file, "w", encoding="utf-8") as file:
        file.write(transcript)

    return transcript, str(transcript_file)