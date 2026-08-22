import os
import random
import re
import time
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yt_dlp

from services.chat_service import answer_from_transcript
from services.processing_service import process_video
from utils.helpers import create_directories


def process_video_with_retry(
    *,
    video_path: str,
    video_name: str,
    status_callback=None,
    progress_callback=None,
    maximum_attempts: int = 4,
):
    """Run the complete pipeline and retry temporary AI service errors.

    This handles temporary Gemini errors such as 503 high demand,
    429 rate limits and network timeouts.
    """

    last_error = None

    for attempt in range(1, maximum_attempts + 1):
        try:
            return process_video(
                video_path=video_path,
                video_name=video_name,
                status_callback=status_callback,
                progress_callback=progress_callback,
            )
        except Exception as error:
            last_error = error
            error_text = str(error).lower()

            temporary_error = any(
                message in error_text
                for message in (
                    "503",
                    "unavailable",
                    "high demand",
                    "429",
                    "resource exhausted",
                    "rate limit",
                    "timeout",
                    "timed out",
                )
            )

            if not temporary_error or attempt == maximum_attempts:
                raise

            wait_seconds = min(15, (2 ** (attempt - 1)) + random.uniform(0.5, 1.5))

            if status_callback:
                status_callback(
                    f"⚠️ AI service is busy. Retrying in {wait_seconds:.0f} seconds "
                    f"(attempt {attempt + 1}/{maximum_attempts})..."
                )

            time.sleep(wait_seconds)

    raise ConnectionError(
        "The AI service is temporarily busy. Please try again in a few minutes."
    ) from last_error


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="DeepDive AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown(
    """
    <style>
        :root {
            --dd-primary: #7c3aed;
            --dd-secondary: #2563eb;
            --dd-accent: #06b6d4;
            --dd-border: rgba(148, 163, 184, 0.20);
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 0%, rgba(124, 58, 237, 0.18), transparent 28%),
                radial-gradient(circle at 96% 4%, rgba(37, 99, 235, 0.15), transparent 25%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.02), transparent 45%);
        }

        html { scroll-behavior: smooth; }

        #MainMenu, footer { visibility: hidden; }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.6rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4 {
            letter-spacing: -0.025em;
        }

        .brand-row {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .brand-mark {
            display: grid;
            place-items: center;
            width: 48px;
            height: 48px;
            border-radius: 15px;
            font-size: 1.45rem;
            background: linear-gradient(135deg, var(--dd-primary), var(--dd-secondary));
            box-shadow: 0 12px 30px rgba(79, 70, 229, 0.28);
        }

        .brand-name {
            font-size: 1.08rem;
            font-weight: 850;
            line-height: 1.1;
        }

        .brand-tagline {
            font-size: 0.78rem;
            opacity: 0.65;
            margin-top: 0.18rem;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.6rem 2.7rem;
            border: 1px solid rgba(124, 58, 237, 0.24);
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(124, 58, 237, 0.19), rgba(37, 99, 235, 0.10) 54%, rgba(6, 182, 212, 0.08));
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
            margin-bottom: 1.6rem;
        }

        .hero::after {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: -80px;
            top: -100px;
            border-radius: 50%;
            background: rgba(255,255,255,0.08);
            filter: blur(2px);
        }

        .hero-actions {
            display: flex;
            gap: 0.7rem;
            flex-wrap: wrap;
            margin-top: 1.3rem;
        }

        .hero-chip {
            border: 1px solid rgba(124, 58, 237, 0.24);
            background: rgba(255,255,255,0.08);
            padding: 0.48rem 0.75rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .hero-badge {
            display: inline-block;
            padding: 0.4rem 0.75rem;
            border-radius: 999px;
            background: rgba(99, 102, 241, 0.14);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-bottom: 0.9rem;
        }

        .main-title {
            font-size: clamp(2.5rem, 6vw, 4.6rem);
            line-height: 1;
            font-weight: 900;
            margin: 0;
            letter-spacing: -0.04em;
        }

        .main-subtitle {
            max-width: 850px;
            font-size: 1.08rem;
            line-height: 1.7;
            opacity: 0.82;
            margin-top: 1rem;
            margin-bottom: 0;
        }

        .feature-card {
            padding: 1.25rem;
            border: 1px solid var(--dd-border);
            border-radius: 20px;
            min-height: 160px;
            background: rgba(255, 255, 255, 0.045);
            backdrop-filter: blur(12px);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.055);
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            border-color: rgba(124, 58, 237, 0.48);
            box-shadow: 0 18px 38px rgba(15, 23, 42, 0.09);
        }

        .feature-icon {
            font-size: 1.7rem;
            margin-bottom: 0.55rem;
        }

        .status-card {
            padding: 1.1rem;
            border-radius: 16px;
            border: 1px solid rgba(128, 128, 128, 0.20);
            background: rgba(255, 255, 255, 0.03);
        }

        .section-label {
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            opacity: 0.62;
            margin-bottom: 0.3rem;
        }

        .flashcard {
            padding: 2.4rem 2rem;
            border: 1px solid rgba(99, 102, 241, 0.35);
            border-radius: 22px;
            min-height: 250px;
            text-align: center;
            margin: 1.2rem 0;
            background: linear-gradient(
                145deg,
                rgba(99, 102, 241, 0.10),
                rgba(14, 165, 233, 0.05)
            );
            box-shadow: 0 16px 38px rgba(15, 23, 42, 0.08);
        }

        .flashcard-label {
            font-size: 0.78rem;
            opacity: 0.65;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 800;
        }

        .flashcard-content {
            font-size: 1.45rem;
            font-weight: 700;
            margin-top: 1.3rem;
            line-height: 1.55;
        }

        .small-text {
            font-size: 0.92rem;
            line-height: 1.55;
            opacity: 0.76;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--dd-border);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            background: rgba(255, 255, 255, 0.045);
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
        }

        div[data-testid="stMetricValue"] {
            font-weight: 850;
        }

        div[data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: rgba(148, 163, 184, 0.08);
            border-radius: 15px;
            padding: 0.35rem;
        }

        button[data-baseweb="tab"] {
            border-radius: 11px;
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }

        div.stButton > button,
        div.stDownloadButton > button {
            width: 100%;
            border-radius: 13px;
            font-weight: 750;
            min-height: 2.9rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(79, 70, 229, 0.16);
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea {
            border-radius: 13px;
        }

        div[data-testid="stFileUploader"] {
            border-radius: 18px;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.18);
        }

        @media (max-width: 760px) {
            .hero {
                padding: 1.5rem;
            }

            .main-subtitle {
                font-size: 0.98rem;
            }

            .feature-card {
                min-height: auto;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CREATE REQUIRED DIRECTORIES
# =========================================================
create_directories()

for folder in [
    "uploads",
    "audio",
    "transcripts",
    "notes",
    "quizzes",
    "flashcards",
    "pdfs",
]:
    Path(folder).mkdir(exist_ok=True)


# =========================================================
# SESSION STATE
# =========================================================
def get_default_values() -> dict:
    return {
        "processed": False,
        "transcript": "",
        "study_notes": "",
        "quiz": [],
        "quiz_text": "",
        "flashcards": [],
        "flashcards_text": "",
        "exam_material": "",
        "exam_difficulty": "Balanced",
        "quiz_submitted": False,
        "quiz_score": 0,
        "flashcard_index": 0,
        "flashcard_revealed": False,
        "chat_messages": [],
        "transcript_file": "",
        "notes_path": "",
        "quiz_path": "",
        "flashcards_path": "",
        "pdf_path": "",
        "audio_path": "",
        "video_name": "",
        "processing_time": 0.0,
        "input_source": "Upload Video",
        "youtube_url": "",
    }


for key, value in get_default_values().items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def clear_results() -> None:
    """Clear all generated results and interactions."""

    for key, value in get_default_values().items():
        st.session_state[key] = value

    quiz_keys = [
        key
        for key in list(st.session_state.keys())
        if key.startswith("quiz_answer_")
    ]

    for key in quiz_keys:
        del st.session_state[key]


def restart_quiz() -> None:
    """Reset the quiz while keeping processed material."""

    st.session_state.quiz_submitted = False
    st.session_state.quiz_score = 0

    quiz_keys = [
        key
        for key in list(st.session_state.keys())
        if key.startswith("quiz_answer_")
    ]

    for key in quiz_keys:
        del st.session_state[key]


def clear_chat() -> None:
    """Clear the chat conversation."""

    st.session_state.chat_messages = []


def previous_flashcard() -> None:
    """Move to the previous flashcard."""

    if st.session_state.flashcard_index > 0:
        st.session_state.flashcard_index -= 1
        st.session_state.flashcard_revealed = False


def next_flashcard() -> None:
    """Move to the next flashcard."""

    total_cards = len(st.session_state.flashcards)

    if st.session_state.flashcard_index < total_cards - 1:
        st.session_state.flashcard_index += 1
        st.session_state.flashcard_revealed = False


def toggle_flashcard() -> None:
    """Show or hide the current flashcard answer."""

    st.session_state.flashcard_revealed = (
        not st.session_state.flashcard_revealed
    )


def is_valid_youtube_url(url: str) -> bool:
    """Return True when the URL appears to be a supported YouTube link."""

    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False

    host = parsed.netloc.lower().split(":")[0]
    valid_hosts = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }

    return parsed.scheme in {"http", "https"} and host in valid_hosts


def safe_filename(value: str, fallback: str = "youtube_video") -> str:
    """Create a Windows-safe filename from a video title."""

    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" ._")
    return cleaned[:120] or fallback


def download_youtube_video(
    url: str,
    status_callback=None,
    progress_callback=None,
) -> tuple[str, str, dict]:
    """Download a public YouTube video and return its path, filename and metadata."""

    if not is_valid_youtube_url(url):
        raise ValueError("Enter a valid YouTube video URL.")

    Path("uploads").mkdir(exist_ok=True)

    if status_callback:
        status_callback("🔗 Reading YouTube video information...")

    if progress_callback:
        progress_callback(5)

    def progress_hook(data: dict) -> None:
        if data.get("status") == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate")

            if total and progress_callback:
                download_percent = downloaded / total
                progress_callback(min(25, 5 + int(download_percent * 20)))

            if status_callback:
                status_callback("⬇️ Downloading the YouTube video...")

        elif data.get("status") == "finished":
            if progress_callback:
                progress_callback(25)
            if status_callback:
                status_callback("✅ YouTube download complete. Preparing analysis...")

    ydl_options = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": "uploads/youtube_%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "progress_hooks": [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            information = ydl.extract_info(url.strip(), download=True)
    except yt_dlp.utils.DownloadError as error:
        message = str(error).replace("ERROR:", "").strip()
        raise ValueError(
            "YouTube download failed. The video may be private, age-restricted, "
            f"region-blocked or unavailable. Details: {message}"
        ) from error

    if information.get("_type") == "playlist":
        entries = information.get("entries") or []
        if not entries:
            raise ValueError("No downloadable video was found at this URL.")
        information = entries[0]

    video_id = information.get("id", "video")
    candidate_paths = list(Path("uploads").glob(f"youtube_{video_id}.*"))
    candidate_paths = [
        path
        for path in candidate_paths
        if path.suffix.lower() not in {".part", ".ytdl", ".json"}
    ]

    if not candidate_paths:
        raise FileNotFoundError("The YouTube video downloaded, but its file could not be located.")

    video_path = max(candidate_paths, key=lambda item: item.stat().st_mtime)
    title = safe_filename(information.get("title", "YouTube video"))
    video_name = f"{title}{video_path.suffix.lower()}"

    return str(video_path), video_name, information


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div class="brand-row">
            <div class="brand-mark">🧠</div>
            <div>
                <div class="brand-name">DeepDive AI</div>
                <div class="brand-tagline">Your intelligent study workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.success("● System ready", icon="✅")

    st.divider()

    st.write("### Processing Pipeline")
    st.write("1. 📤 Upload video or paste YouTube URL")
    st.write("2. 🎵 Extract audio")
    st.write("3. 🎙️ Generate transcript")
    st.write("4. 🧠 Create study notes")
    st.write("5. ❓ Generate quiz")
    st.write("6. 🗂️ Generate flashcards")
    st.write("7. 💬 Chat with the lecture")
    st.write("8. 📄 Create PDF")

    st.divider()

    st.write("### Technologies")
    st.write("- Python")
    st.write("- Streamlit")
    st.write("- OpenAI Whisper")
    st.write("- Google Gemini")
    st.write("- MoviePy")
    st.write("- FFmpeg")
    st.write("- ReportLab")
    st.write("- yt-dlp")

    st.divider()

    if st.button(
        "🗑️ Clear Current Results",
        key="clear_results_button",
    ):
        clear_results()
        st.rerun()


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">AI-POWERED LEARNING WORKSPACE</div>
        <p class="main-title">DeepDive AI</p>
        <p class="main-subtitle">
            Turn any lecture into a complete, organized learning pack—with
            transcripts, notes, quizzes, flashcards, audio and grounded AI chat.
        </p>
        <div class="hero-actions">
            <span class="hero-chip">⚡ Faster revision</span>
            <span class="hero-chip">🎯 Focused learning</span>
            <span class="hero-chip">📥 Export-ready</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FEATURE CARDS
# =========================================================
feature_col1, feature_col2, feature_col3, feature_col4 = st.columns(4)

with feature_col1:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-icon">🎙️</div>
            <h4>Transcription</h4>
            <p class="small-text">
                Converts lecture speech into searchable text using Whisper.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feature_col2:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <h4>Study Material</h4>
            <p class="small-text">
                Generates notes, key points, keywords and revision content.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feature_col3:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-icon">❓</div>
            <h4>Quiz & Flashcards</h4>
            <p class="small-text">
                Tests understanding and provides interactive revision cards.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with feature_col4:
    st.markdown(
        """
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <h4>Lecture Chat</h4>
            <p class="small-text">
                Answers questions using only the processed lecture transcript.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.divider()


# =========================================================
# VIDEO INPUT
# =========================================================
st.markdown('<div class="section-label">Start here</div>', unsafe_allow_html=True)
st.write("## 🎬 Start a New Deep Dive")
st.caption("Upload a lecture file or paste a public YouTube link. DeepDive will build the complete learning pack for you.")

input_source = st.radio(
    "Select input method",
    options=["Upload Video", "YouTube URL"],
    horizontal=True,
    key="input_source",
)

video_path = ""
video_name = ""
generate_clicked = False

if input_source == "Upload Video":
    uploaded_video = st.file_uploader(
        "Choose a video file",
        type=["mp4", "mov", "avi", "mkv"],
        help="Supported formats: MP4, MOV, AVI and MKV. Short videos are faster to process.",
        key="lecture_video_uploader",
    )

    if uploaded_video is not None:
        video_path = os.path.join("uploads", uploaded_video.name)
        video_name = uploaded_video.name

        with open(video_path, "wb") as video_file:
            video_file.write(uploaded_video.getbuffer())

        video_column, information_column = st.columns([2, 1])

        with video_column:
            st.write("### Video Preview")
            st.video(video_path)

        with information_column:
            st.write("### Video Information")
            file_size_mb = uploaded_video.size / (1024 * 1024)

            safe_video_name = escape(uploaded_video.name)
            st.markdown(
                f"""<div class="status-card">
<b>Input source</b><br>
Uploaded file<br><br>
<b>File name</b><br>
{safe_video_name}<br><br>
<b>File size</b><br>
{file_size_mb:.2f} MB<br><br>
<b>Status</b><br>
Ready for processing
</div>""",
                unsafe_allow_html=True,
            )

            generate_clicked = st.button(
                "🚀 Generate Study Material",
                type="primary",
                key="generate_uploaded_material_button",
            )
    else:
        st.info("Upload an MP4, MOV, AVI or MKV video to begin.")

else:
    youtube_url = st.text_input(
        "Paste a YouTube video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key="youtube_url",
        help="Use a public YouTube video. Private, members-only or restricted videos may not download.",
    ).strip()

    if youtube_url:
        if is_valid_youtube_url(youtube_url):
            preview_column, information_column = st.columns([2, 1])

            with preview_column:
                st.write("### YouTube Preview")
                st.video(youtube_url)

            with information_column:
                st.write("### URL Information")
                st.markdown(
                    """
                    <div class="status-card">
                        <b>Input source</b><br>
                        YouTube URL<br><br>

                        <b>Status</b><br>
                        Ready to download and process<br><br>

                        <b>Note</b><br>
                        Processing begins after the video is downloaded.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                generate_clicked = st.button(
                    "🚀 Analyze YouTube Video",
                    type="primary",
                    key="generate_youtube_material_button",
                )
        else:
            st.error("Enter a valid YouTube URL, such as https://youtu.be/VIDEO_ID.")
    else:
        st.info("Paste a public YouTube video URL to begin.")


if generate_clicked:
    progress_bar = st.progress(0)
    status_message = st.empty()

    def update_status(message: str) -> None:
        status_message.info(message)

    def update_progress(progress: int) -> None:
        progress_bar.progress(max(0, min(100, progress)))

    try:
        if input_source == "YouTube URL":
            video_path, video_name, youtube_info = download_youtube_video(
                url=st.session_state.youtube_url,
                status_callback=update_status,
                progress_callback=update_progress,
            )

            st.caption(
                f"Downloaded: {youtube_info.get('title', video_name)}"
                + (
                    f" • Channel: {youtube_info.get('uploader')}"
                    if youtube_info.get("uploader")
                    else ""
                )
            )
        else:
            update_progress(5)

        results = process_video_with_retry(
            video_path=video_path,
            video_name=video_name,
            status_callback=update_status,
            progress_callback=update_progress,
        )

        st.session_state.processed = True
        st.session_state.transcript = results["transcript"]
        st.session_state.study_notes = results["study_notes"]
        st.session_state.quiz = results["quiz"]
        st.session_state.quiz_text = results["quiz_text"]
        st.session_state.flashcards = results["flashcards"]
        st.session_state.flashcards_text = results["flashcards_text"]
        st.session_state.transcript_file = results["transcript_file"]
        st.session_state.notes_path = results["notes_path"]
        st.session_state.quiz_path = results["quiz_path"]
        st.session_state.flashcards_path = results["flashcards_path"]
        st.session_state.pdf_path = results["pdf_path"]
        st.session_state.audio_path = results["audio_path"]
        st.session_state.video_name = results["video_name"]
        st.session_state.processing_time = results["processing_time"]

        st.session_state.quiz_submitted = False
        st.session_state.quiz_score = 0
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_revealed = False
        st.session_state.chat_messages = []

        progress_bar.progress(100)
        status_message.success("🎉 Your complete learning pack is ready!")
        st.toast("Deep Dive completed successfully!", icon="✅")
        st.balloons()

    except ValueError as error:
        progress_bar.empty()
        status_message.empty()
        st.error(str(error))

    except ConnectionError as error:
        progress_bar.empty()
        status_message.empty()
        st.error(str(error))

    except TimeoutError as error:
        progress_bar.empty()
        status_message.empty()
        st.error(str(error))

    except Exception as error:
        progress_bar.empty()
        status_message.empty()
        st.error(f"Processing failed: {error}")


# =========================================================
# RESULTS DASHBOARD
# =========================================================
if st.session_state.processed:
    st.divider()

    st.markdown('<div class="section-label">Learning analytics</div>', unsafe_allow_html=True)
    st.write("## 📊 Processing Overview")

    transcript_word_count = len(
        st.session_state.transcript.split()
    )

    reading_time = max(
        1,
        round(transcript_word_count / 200),
    )

    processing_time = round(
        st.session_state.processing_time,
        1,
    )

    quiz_count = len(st.session_state.quiz)
    flashcard_count = len(st.session_state.flashcards)

    (
        metric_col1,
        metric_col2,
        metric_col3,
        metric_col4,
        metric_col5,
    ) = st.columns(5)

    with metric_col1:
        st.metric("Transcript Words", transcript_word_count)

    with metric_col2:
        st.metric("Reading Time", f"{reading_time} min")

    with metric_col3:
        st.metric("Processing Time", f"{processing_time} sec")

    with metric_col4:
        st.metric("Quiz Questions", quiz_count)

    with metric_col5:
        st.metric("Flashcards", flashcard_count)

    st.caption(
        f"Processed video: {st.session_state.video_name}"
    )

    st.markdown('<div class="section-label">Explore your results</div>', unsafe_allow_html=True)
    st.write("## 📚 Generated Learning Material")

    (
        transcript_tab,
        notes_tab,
        quiz_tab,
        flashcards_tab,
        exam_tab,
        chat_tab,
        audio_tab,
        downloads_tab,
    ) = st.tabs(
        [
            "📝 Transcript",
            "🧠 Study Notes",
            "❓ Interactive Quiz",
            "🗂️ Flashcards",
            "🎓 Exam Mode",
            "💬 Ask DeepDive",
            "🎵 Audio",
            "📥 Export",
        ]
    )


    # =====================================================
    # TRANSCRIPT TAB
    # =====================================================
    with transcript_tab:
        st.text_area(
            "Complete generated transcript",
            value=st.session_state.transcript,
            height=450,
            key="transcript_text_area",
        )

        st.caption(
            f"Saved to: {st.session_state.transcript_file}"
        )


    # =====================================================
    # STUDY NOTES TAB
    # =====================================================
    with notes_tab:
        st.markdown(st.session_state.study_notes)

        st.caption(
            f"Saved to: {st.session_state.notes_path}"
        )


    # =====================================================
    # INTERACTIVE QUIZ TAB
    # =====================================================
    with quiz_tab:
        st.write("### ❓ Test Your Understanding")

        st.caption(
            "Answer every question and click Submit Quiz."
        )

        quiz_items = st.session_state.quiz
        option_letters = ["A", "B", "C", "D"]

        with st.form("interactive_quiz_form"):
            selected_answers = []

            for question_index, item in enumerate(quiz_items):
                st.markdown(
                    f"### Question {question_index + 1}"
                )

                st.write(item["question"])

                formatted_options = [
                    f"{option_letters[index]}. {option}"
                    for index, option in enumerate(
                        item["options"]
                    )
                ]

                selected_option = st.radio(
                    "Select your answer:",
                    options=list(range(4)),
                    format_func=(
                        lambda index,
                        options=formatted_options: options[index]
                    ),
                    key=f"quiz_answer_{question_index}",
                    index=None,
                )

                selected_answers.append(selected_option)

                st.divider()

            submit_quiz = st.form_submit_button(
                "✅ Submit Quiz",
                type="primary",
            )

        if submit_quiz:
            unanswered_questions = sum(
                answer is None
                for answer in selected_answers
            )

            if unanswered_questions > 0:
                st.warning(
                    f"Please answer all questions. "
                    f"{unanswered_questions} question(s) remain."
                )

            else:
                score = 0

                for question_index, item in enumerate(
                    quiz_items
                ):
                    if (
                        selected_answers[question_index]
                        == item["correct_answer"]
                    ):
                        score += 1

                st.session_state.quiz_score = score
                st.session_state.quiz_submitted = True

        if st.session_state.quiz_submitted:
            score = st.session_state.quiz_score
            total_questions = len(quiz_items)

            percentage = round(
                score / total_questions * 100
            )

            st.divider()
            st.write("## 📊 Quiz Result")

            score_col1, score_col2, score_col3 = st.columns(3)

            with score_col1:
                st.metric(
                    "Score",
                    f"{score}/{total_questions}",
                )

            with score_col2:
                st.metric(
                    "Percentage",
                    f"{percentage}%",
                )

            with score_col3:
                if percentage >= 80:
                    performance = "Excellent"
                elif percentage >= 60:
                    performance = "Good"
                elif percentage >= 40:
                    performance = "Average"
                else:
                    performance = "Needs Revision"

                st.metric(
                    "Performance",
                    performance,
                )

            if percentage >= 80:
                st.success(
                    "Excellent work! You understood the lecture well."
                )
            elif percentage >= 60:
                st.info(
                    "Good attempt. Review a few concepts and try again."
                )
            elif percentage >= 40:
                st.warning(
                    "Some concepts need more revision."
                )
            else:
                st.error(
                    "Review the notes carefully and restart the quiz."
                )

            st.write("## Answer Review")

            for question_index, item in enumerate(
                quiz_items
            ):
                selected_answer = st.session_state.get(
                    f"quiz_answer_{question_index}"
                )

                correct_answer = item["correct_answer"]

                st.write(
                    f"### Question {question_index + 1}"
                )

                st.write(item["question"])

                if selected_answer == correct_answer:
                    st.success(
                        f"Correct: "
                        f"{option_letters[correct_answer]}. "
                        f"{item['options'][correct_answer]}"
                    )
                else:
                    if selected_answer is not None:
                        st.error(
                            f"Your answer: "
                            f"{option_letters[selected_answer]}. "
                            f"{item['options'][selected_answer]}"
                        )

                    st.success(
                        f"Correct answer: "
                        f"{option_letters[correct_answer]}. "
                        f"{item['options'][correct_answer]}"
                    )

                if item.get("explanation"):
                    st.info(
                        f"Explanation: {item['explanation']}"
                    )

                st.divider()

            if st.button(
                "🔄 Restart Quiz",
                key="restart_quiz_button",
            ):
                restart_quiz()
                st.rerun()


    # =====================================================
    # FLASHCARDS TAB
    # =====================================================
    with flashcards_tab:
        st.write("### 🗂️ Revision Flashcards")

        flashcards = st.session_state.flashcards

        if flashcards:
            total_flashcards = len(flashcards)

            current_index = min(
                st.session_state.flashcard_index,
                total_flashcards - 1,
            )

            current_card = flashcards[current_index]

            st.progress(
                (current_index + 1) / total_flashcards
            )

            st.caption(
                f"Flashcard {current_index + 1} "
                f"of {total_flashcards}"
            )

            if st.session_state.flashcard_revealed:
                card_label = "Answer"
                card_content = current_card["back"]
            else:
                card_label = "Question"
                card_content = current_card["front"]

            st.markdown(
                f"""
                <div class="flashcard">
                    <div class="flashcard-label">
                        {card_label}
                    </div>

                    <div class="flashcard-content">
                        {card_content}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            (
                navigation_col1,
                navigation_col2,
                navigation_col3,
            ) = st.columns([1, 2, 1])

            with navigation_col1:
                st.button(
                    "⬅️ Previous",
                    on_click=previous_flashcard,
                    disabled=current_index == 0,
                    key="previous_flashcard_button",
                )

            with navigation_col2:
                answer_button_text = (
                    "🙈 Hide Answer"
                    if st.session_state.flashcard_revealed
                    else "👁️ Show Answer"
                )

                st.button(
                    answer_button_text,
                    on_click=toggle_flashcard,
                    type="primary",
                    key="toggle_flashcard_button",
                )

            with navigation_col3:
                st.button(
                    "Next ➡️",
                    on_click=next_flashcard,
                    disabled=(
                        current_index == total_flashcards - 1
                    ),
                    key="next_flashcard_button",
                )

            st.divider()

            with st.expander("View All Flashcards"):
                for card_number, card in enumerate(
                    flashcards,
                    start=1,
                ):
                    st.write(
                        f"### Flashcard {card_number}"
                    )

                    st.write(
                        f"**Front:** {card['front']}"
                    )

                    st.write(
                        f"**Back:** {card['back']}"
                    )

                    st.divider()

            st.download_button(
                label="📥 Download Flashcards",
                data=st.session_state.flashcards_text,
                file_name=(
                    f"{Path(st.session_state.video_name).stem}"
                    "_flashcards.txt"
                ),
                mime="text/plain",
                key="download_flashcards_flashcard_tab",
            )

        else:
            st.warning("No flashcards were generated.")


    # =====================================================
    # EXAM MODE TAB
    # =====================================================
    with exam_tab:
        st.write("### 🎓 Exam Preparation Mode")
        st.caption(
            "Generate exam-ready questions and answers only when needed. "
            "This keeps the main video processing faster."
        )

        exam_col1, exam_col2 = st.columns([2, 1])

        with exam_col1:
            exam_difficulty = st.selectbox(
                "Difficulty level",
                ["Easy", "Balanced", "Advanced"],
                index=["Easy", "Balanced", "Advanced"].index(
                    st.session_state.exam_difficulty
                ),
                key="exam_difficulty_selector",
            )

        with exam_col2:
            include_answers = st.toggle(
                "Include model answers",
                value=True,
                key="exam_include_answers",
            )

        st.info(
            "Exam Mode creates 2-mark, 5-mark, 10-mark, viva and MCQ "
            "questions directly from the processed lecture."
        )

        generate_exam = st.button(
            "✨ Generate Exam Material",
            type="primary",
            use_container_width=True,
            key="generate_exam_material_button",
        )

        if generate_exam:
            st.session_state.exam_difficulty = exam_difficulty

            answer_instruction = (
                "Include a clear model answer immediately after every question."
                if include_answers
                else "Do not include answers. Produce questions only."
            )

            exam_prompt = f"""
Create exam preparation material using ONLY the lecture transcript.

Difficulty: {exam_difficulty}
{answer_instruction}

Return well-formatted Markdown with exactly these sections:

# 🎓 Exam Preparation Pack
## 1. Two-Mark Questions
Create 8 concise questions.

## 2. Five-Mark Questions
Create 5 descriptive questions.

## 3. Ten-Mark Questions
Create 3 detailed long-answer questions.

## 4. Viva Questions
Create 10 short viva questions.

## 5. Multiple-Choice Questions
Create 10 MCQs with four options labelled A, B, C and D.
If answers are requested, clearly state the correct option and give a one-line explanation.

Rules:
- Stay strictly grounded in the transcript.
- Do not invent topics not covered in the lecture.
- Avoid duplicate questions.
- Use simple, exam-ready language.
- For model answers, match the depth to the marks allocated.
"""

            try:
                with st.spinner("Deep Dive is preparing your exam pack..."):
                    st.session_state.exam_material = answer_from_transcript(
                        transcript=st.session_state.transcript,
                        question=exam_prompt,
                        chat_history=[],
                    )

                st.toast("Exam preparation pack generated!", icon="🎓")

            except (ValueError, ConnectionError, TimeoutError) as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"Exam Mode failed: {error}")

        if st.session_state.exam_material:
            st.divider()
            st.markdown(st.session_state.exam_material)

            exam_file_stem = Path(st.session_state.video_name).stem
            st.download_button(
                "📥 Download Exam Preparation Pack",
                data=st.session_state.exam_material,
                file_name=f"{exam_file_stem}_exam_pack.md",
                mime="text/markdown",
                use_container_width=True,
                key="download_exam_pack_exam_tab",
            )
        else:
            st.caption(
                "No exam pack has been generated yet. Click the button above after "
                "processing a lecture."
            )


    # =====================================================
    # CHAT WITH VIDEO TAB
    # =====================================================
    with chat_tab:
        chat_heading_col, clear_chat_col = st.columns([4, 1])

        with chat_heading_col:
            st.write("### 💬 Ask DeepDive About the Lecture")
            st.caption(
                "Answers are generated by Gemini using only the processed lecture transcript."
            )

        with clear_chat_col:
            if st.button(
                "Clear Chat",
                key="clear_chat_button",
            ):
                clear_chat()
                st.rerun()

        if not st.session_state.chat_messages:
            st.info(
                "Ask a question such as:\n\n"
                "- What is Python?\n"
                "- What applications of Python were discussed?\n"
                "- Summarize the main idea in simple language."
            )

        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_question = st.chat_input(
            "Ask a question about the processed lecture...",
            key="video_chat_input",
        )

        if user_question:
            st.session_state.chat_messages.append(
                {
                    "role": "user",
                    "content": user_question,
                }
            )

            with st.chat_message("user"):
                st.markdown(user_question)

            previous_history = st.session_state.chat_messages[:-1]

            try:
                with st.chat_message("assistant"):
                    with st.spinner(
                        "Gemini is reviewing the lecture transcript..."
                    ):
                        answer = answer_from_transcript(
                            transcript=st.session_state.transcript,
                            question=user_question,
                            chat_history=previous_history,
                        )

                    st.markdown(answer)

                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except ValueError as error:
                st.error(str(error))

            except ConnectionError as error:
                st.error(str(error))

            except TimeoutError as error:
                st.error(str(error))

            except Exception as error:
                st.error(
                    f"Chat failed: {error}"
                )


    # =====================================================
    # AUDIO TAB
    # =====================================================
    with audio_tab:
        if (
            st.session_state.audio_path
            and os.path.exists(
                st.session_state.audio_path
            )
        ):
            st.audio(
                st.session_state.audio_path
            )

            st.caption(
                f"Saved to: {st.session_state.audio_path}"
            )

        else:
            st.warning(
                "The extracted audio file is unavailable."
            )


    # =====================================================
    # DOWNLOADS TAB
    # =====================================================
    with downloads_tab:
        st.write("### 📥 Download Generated Files")

        video_stem = Path(
            st.session_state.video_name
        ).stem

        download_col1, download_col2 = st.columns(2)
        download_col3, download_col4 = st.columns(2)
        download_col5, download_col6 = st.columns(2)

        with download_col1:
            st.download_button(
                label="📥 Download Transcript",
                data=st.session_state.transcript,
                file_name=f"{video_stem}_transcript.txt",
                mime="text/plain",
                key="download_transcript_downloads_tab",
            )

        with download_col2:
            st.download_button(
                label="📥 Download Study Notes",
                data=st.session_state.study_notes,
                file_name=f"{video_stem}_notes.txt",
                mime="text/plain",
                key="download_notes_downloads_tab",
            )

        with download_col3:
            st.download_button(
                label="📥 Download Quiz with Answers",
                data=st.session_state.quiz_text,
                file_name=f"{video_stem}_quiz.txt",
                mime="text/plain",
                key="download_quiz_downloads_tab",
            )

        with download_col4:
            st.download_button(
                label="📥 Download Flashcards",
                data=st.session_state.flashcards_text,
                file_name=f"{video_stem}_flashcards.txt",
                mime="text/plain",
                key="download_flashcards_downloads_tab",
            )

        with download_col5:
            if st.session_state.exam_material:
                st.download_button(
                    label="🎓 Download Exam Pack",
                    data=st.session_state.exam_material,
                    file_name=f"{video_stem}_exam_pack.md",
                    mime="text/markdown",
                    key="download_exam_pack_downloads_tab",
                )
            else:
                st.info("Generate an Exam Pack from the Exam Mode tab.")

        with download_col6:
            if (
                st.session_state.pdf_path
                and os.path.exists(
                    st.session_state.pdf_path
                )
            ):
                with open(
                    st.session_state.pdf_path,
                    "rb",
                ) as pdf_file:
                    pdf_data = pdf_file.read()

                st.download_button(
                    label="📄 Download PDF Notes",
                    data=pdf_data,
                    file_name=os.path.basename(
                        st.session_state.pdf_path
                    ),
                    mime="application/pdf",
                    type="primary",
                    key="download_pdf_downloads_tab",
                )
            else:
                st.warning("The PDF file is unavailable.")