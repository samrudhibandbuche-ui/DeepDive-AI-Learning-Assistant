from pathlib import Path

from moviepy import VideoFileClip


def extract_audio(video_path: str) -> str:
    """Extract audio from a video and save it as a WAV file."""

    video_file = Path(video_path)

    audio_folder = Path("audio")
    audio_folder.mkdir(exist_ok=True)

    audio_path = audio_folder / f"{video_file.stem}.wav"

    video_clip = VideoFileClip(str(video_file))

    try:
        if video_clip.audio is None:
            raise ValueError("The selected video does not contain audio.")

        video_clip.audio.write_audiofile(
            str(audio_path),
            codec="pcm_s16le",
            logger=None,
        )
    finally:
        video_clip.close()

    return str(audio_path)
