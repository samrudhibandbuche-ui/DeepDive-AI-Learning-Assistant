from pathlib import Path

import streamlit as st
import whisper
import whisper.audio


@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")


def transcribe_audio(audio_path: str):
    """Convert audio into text using OpenAI Whisper."""

    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(
            f"Audio file was not found: {audio_file}"
        )

    if audio_file.stat().st_size == 0:
        raise ValueError(
            "The extracted audio file is empty."
        )

    # Load the audio through Whisper's audio loader.
    # This also ensures FFmpeg is available.
    try:
        audio = whisper.audio.load_audio(str(audio_file))
    except Exception as error:
        raise RuntimeError(
            f"Whisper could not load the audio file: {error}"
        ) from error

    if audio is None or len(audio) == 0:
        raise ValueError(
            "The extracted audio contains no usable audio data."
        )

    model = load_whisper_model()

    try:
        result = model.transcribe(
            audio,
            fp16=False,
        )
    except Exception as error:
        raise RuntimeError(
            f"Whisper transcription failed: {error}"
        ) from error

    transcript = result.get("text", "").strip()

    if not transcript:
        raise ValueError(
            "Whisper could not detect any speech in the video."
        )

    transcript_folder = Path("transcripts")
    transcript_folder.mkdir(exist_ok=True)

    transcript_file = (
        transcript_folder
        / f"{audio_file.stem}.txt"
    )

    with open(
        transcript_file,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(transcript)

    return transcript, str(transcript_file)