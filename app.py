import html
import os
import imageio_ffmpeg

# Get FFmpeg bundled with imageio-ffmpeg
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(ffmpeg_path)

# Make FFmpeg available as "ffmpeg"
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
os.environ["FFMPEG_BINARY"] = ffmpeg_path

# Create an "ffmpeg" command if it doesn't already exist
ffmpeg_command = os.path.join(ffmpeg_dir, "ffmpeg")

if not os.path.exists(ffmpeg_command):
    try:
        os.symlink(ffmpeg_path, ffmpeg_command)
    except FileExistsError:
        pass

import re
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yt_dlp

from services.chat_service import answer_from_transcript
from services.demo_service import answer_demo_question, get_demo_results
from services.processing_service import process_video
from utils.helpers import create_directories


# =========================================================
# STYLE LOADER
# =========================================================
def load_css(relative_path: str) -> None:
    """Load the external stylesheet used by the DeepDive interface."""

    css_path = Path(__file__).resolve().parent / relative_path

    try:
        css = css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        st.warning(
            "The interface stylesheet could not be found at "
            f"{css_path}. The app will continue with Streamlit's default styling."
        )
        return
    except OSError as error:
        st.warning(f"The interface stylesheet could not be loaded: {error}")
        return

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="DeepDive AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css("assets/css/style.css")


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
        "uploader_version": 0,
        "demo_mode": False,
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


def remove_uploaded_video() -> None:
    """Reset the uploader so the user can select another video."""

    st.session_state.uploader_version += 1


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


def save_results_to_session(results: dict) -> None:
    """Store a generated or demonstration learning pack in session state."""

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
    st.session_state.demo_mode = bool(results.get("demo_mode", False))
    st.session_state.quiz_submitted = False
    st.session_state.quiz_score = 0
    st.session_state.flashcard_index = 0
    st.session_state.flashcard_revealed = False
    st.session_state.chat_messages = []


def is_quota_error(error: Exception) -> bool:
    """Recognize Gemini quota/rate-limit errors without exposing raw details."""

    message = str(error).lower()
    quota_markers = (
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "429",
        "generativelanguage.googleapis.com",
    )
    return any(marker in message for marker in quota_markers)


def show_processing_error(error: Exception) -> None:
    """Show a presentation-safe message for processing failures."""

    if is_quota_error(error):
        st.error(
            "The AI service has reached its current request limit. "
            "Please try again after the quota resets or use Presentation Demo."
        )
    else:
        st.error(
            "The video could not be processed right now. "
            "Please check the input and try again."
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
        <div class="sidebar-brand-card">
            <div class="sidebar-logo-circle">🧠</div>
            <div class="sidebar-brand-title">DeepDive AI</div>
            <div class="sidebar-brand-subtitle">Smart Video Learning<br>Platform</div>
        </div>

        <nav class="sidebar-navigation" aria-label="DeepDive navigation">
            <a class="sidebar-nav-item active" href="#home-section">⌂ <span>Home</span></a>
            <a class="sidebar-nav-item" href="#upload-section">☁ <span>Upload</span></a>
            <a class="sidebar-nav-item" href="#results-section">▤ <span>Notes</span></a>
            <a class="sidebar-nav-item" href="#results-section">▣ <span>Flashcards</span></a>
            <a class="sidebar-nav-item" href="#results-section">? <span>Quiz</span></a>
            <a class="sidebar-nav-item" href="#results-section">◌ <span>Chat</span></a>
            <a class="sidebar-nav-item" href="#results-section">⇩ <span>Downloads</span></a>
        </nav>

        <div class="pipeline-card">
            <div class="pipeline-title">Processing Pipeline</div>
            <div class="pipeline-step complete"><span class="pipeline-dot">✓</span><span>Upload</span></div>
            <div class="pipeline-line complete-line"></div>
            <div class="pipeline-step complete"><span class="pipeline-dot">✓</span><span>Audio Extraction</span></div>
            <div class="pipeline-line active-line"></div>
            <div class="pipeline-step active-step"><span class="pipeline-dot">●</span><span>Transcription</span></div>
            <div class="pipeline-line"></div>
            <div class="pipeline-step"><span class="pipeline-dot empty-dot"></span><span>Notes Generation</span></div>
            <div class="pipeline-line"></div>
            <div class="pipeline-step"><span class="pipeline-dot empty-dot"></span><span>Quiz Generation</span></div>
            <div class="pipeline-line"></div>
            <div class="pipeline-step"><span class="pipeline-dot empty-dot"></span><span>Flashcards</span></div>
            <div class="pipeline-line"></div>
            <div class="pipeline-step"><span class="pipeline-dot empty-dot"></span><span>PDF Export</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🗑️ Clear Current Results",
        key="clear_results_button",
        use_container_width=True,
    ):
        clear_results()
        st.rerun()


# =========================================================
# HEADER
# =========================================================
st.markdown('<div id="home-section"></div>', unsafe_allow_html=True)
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
# VIDEO INPUT
# =========================================================
st.markdown('<div id="upload-section"></div>', unsafe_allow_html=True)

video_path = ""
video_name = ""
generate_clicked = False

with st.container(border=True):
    st.markdown('<div class="upload-card-marker"></div>', unsafe_allow_html=True)

    upload_heading_col, upload_method_col = st.columns([1.25, 1])

    with upload_heading_col:
        st.markdown(
            """
            <div class="upload-heading-row">
                <div class="upload-heading-icon">🎬</div>
                <div>
                    <div class="upload-heading-title">Start a New DeepDive</div>
                    <div class="upload-heading-subtitle">
                        Upload a lecture video or paste a YouTube link to get
                        detailed study materials.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with upload_method_col:
        input_source = st.radio(
            "Select input method",
            options=["Upload Video", "YouTube URL", "Presentation Demo"],
            horizontal=True,
            key="input_source",
            label_visibility="collapsed",
        )

    upload_content_col, upload_info_col = st.columns([3.15, 1.25], gap="large")

    uploaded_video = None
    youtube_url = ""
    file_size_mb = None

    with upload_content_col:
        if input_source == "Upload Video":
            uploaded_video = st.file_uploader(
                "Drag & drop your video here",
                type=["mp4", "mov", "avi", "mkv"],
                help="Supported formats: MP4, MOV, AVI and MKV. Short videos are faster to process.",
                key=f"lecture_video_uploader_{st.session_state.uploader_version}",
            )

            if uploaded_video is not None:
                video_path = os.path.join("uploads", uploaded_video.name)
                video_name = uploaded_video.name
                file_size_mb = uploaded_video.size / (1024 * 1024)

                with open(video_path, "wb") as video_file:
                    video_file.write(uploaded_video.getbuffer())

                safe_uploaded_name = html.escape(uploaded_video.name)

                st.markdown(
                    f"""
                    <div class="custom-uploaded-file-card">
                        <div class="custom-uploaded-file-icon">🎬</div>
                        <div class="custom-uploaded-file-copy">
                            <div class="custom-uploaded-file-label">Uploaded lecture</div>
                            <div class="custom-uploaded-file-name">{safe_uploaded_name}</div>
                            <div class="custom-uploaded-file-meta">
                                <span>▧ {file_size_mb:.2f} MB</span>
                                <span class="custom-ready-pill">● Ready to analyze</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                file_action_col, preview_action_col = st.columns([1, 2])

                with file_action_col:
                    if st.button(
                        "🗑 Remove file",
                        key="remove_uploaded_video_button",
                        use_container_width=True,
                    ):
                        remove_uploaded_video()
                        st.rerun()

                with preview_action_col:
                    with st.expander("▶ Preview uploaded video"):
                        st.video(video_path)

                generate_clicked = st.button(
                    "✦ Analyze Video",
                    type="primary",
                    key="generate_uploaded_material_button",
                    use_container_width=True,
                )
            else:
                st.caption("Supports MP4, MOV, AVI and MKV files.")
                st.button(
                    "✦ Analyze Video",
                    type="primary",
                    key="disabled_uploaded_material_button",
                    use_container_width=True,
                    disabled=True,
                )

        elif input_source == "YouTube URL":
            youtube_url = st.text_input(
                "Paste a YouTube video URL",
                placeholder="https://www.youtube.com/watch?v=...",
                key="youtube_url",
                help="Use a public YouTube video. Private, members-only or restricted videos may not download.",
            ).strip()

            if youtube_url and is_valid_youtube_url(youtube_url):
                with st.expander("Preview YouTube video"):
                    st.video(youtube_url)

                generate_clicked = st.button(
                    "✦ Analyze Video",
                    type="primary",
                    key="generate_youtube_material_button",
                    use_container_width=True,
                )
            elif youtube_url:
                st.error("Enter a valid YouTube URL, such as https://youtu.be/VIDEO_ID.")
                st.button(
                    "✦ Analyze Video",
                    type="primary",
                    key="disabled_invalid_youtube_button",
                    use_container_width=True,
                    disabled=True,
                )
            else:
                st.caption("Paste a public YouTube link above to begin.")
                st.button(
                    "✦ Analyze Video",
                    type="primary",
                    key="disabled_youtube_material_button",
                    use_container_width=True,
                    disabled=True,
                )

        else:
            st.info(
                "Presentation Demo loads a complete sample learning pack "
                "without using Gemini, YouTube or an internet connection."
            )
            generate_clicked = st.button(
                "✦ Load Demo Learning Pack",
                type="primary",
                key="load_presentation_demo_button",
                use_container_width=True,
            )

    with upload_info_col:
        if input_source == "Upload Video" and uploaded_video is not None:
            display_name = html.escape(uploaded_video.name)
            display_size = f"{file_size_mb:.2f} MB"
            display_status = "Ready"
        elif input_source == "YouTube URL" and youtube_url and is_valid_youtube_url(youtube_url):
            display_name = "YouTube video"
            display_size = "Online source"
            display_status = "Ready"
        elif input_source == "Presentation Demo":
            display_name = "Python Basics Demo"
            display_size = "Offline sample"
            display_status = "Ready"
        else:
            display_name = "—"
            display_size = "—"
            display_status = "Not started"

        st.markdown(
            f"""
            <div class="video-info-card">
                <div class="video-info-row"><span>◷&nbsp; Video Name</span><strong>{display_name}</strong></div>
                <div class="video-info-row"><span>◷&nbsp; Duration</span><strong>—</strong></div>
                <div class="video-info-row"><span>▧&nbsp; File Size</span><strong>{display_size}</strong></div>
                <div class="video-info-row status-row">
                    <span>◷&nbsp; Status</span>
                    <strong><i class="status-indicator"></i>{display_status}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if generate_clicked:
    progress_bar = st.progress(0)
    status_message = st.empty()

    def update_status(message: str) -> None:
        status_message.info(message)

    def update_progress(progress: int) -> None:
        progress_bar.progress(max(0, min(100, progress)))

    try:
        if input_source == "Presentation Demo":
            results = get_demo_results(
                status_callback=update_status,
                progress_callback=update_progress,
            )
        else:
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

            results = process_video(
                video_path=video_path,
                video_name=video_name,
                status_callback=update_status,
                progress_callback=update_progress,
            )

        save_results_to_session(results)

        progress_bar.progress(100)
        status_message.success("🎉 Your complete learning pack is ready!")
        st.toast("Deep Dive completed successfully!", icon="✅")
        

    except ValueError as error:
        progress_bar.empty()
        status_message.empty()
        show_processing_error(error)

    except ConnectionError as error:
        progress_bar.empty()
        status_message.empty()
        show_processing_error(error)

    except TimeoutError as error:
        progress_bar.empty()
        status_message.empty()
        show_processing_error(error)

    except Exception as error:
      progress_bar.empty()
      status_message.empty()

      st.error("❌ Video processing failed.")
      st.exception(error)


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
# RESULTS DASHBOARD
# =========================================================
if st.session_state.processed:
    st.markdown('<div id="results-section"></div>', unsafe_allow_html=True)
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
        chat_tab,
        audio_tab,
        downloads_tab,
    ) = st.tabs(
        [
            "📝 Transcript",
            "🧠 Study Notes",
            "❓ Interactive Quiz",
            "🗂️ Flashcards",
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
    # CHAT WITH VIDEO TAB
    # =====================================================
    with chat_tab:
        chat_heading_col, clear_chat_col = st.columns([4, 1])

        with chat_heading_col:
            st.write("### 💬 Ask DeepDive About the Lecture")
            if st.session_state.demo_mode:
                st.caption(
                    "Presentation Demo answers locally from the sample lecture."
                )
            else:
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
                    with st.spinner("Reviewing the lecture transcript..."):
                        if st.session_state.demo_mode:
                            answer = answer_demo_question(user_question)
                        else:
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
                if is_quota_error(error):
                    st.error(
                        "The AI chat request limit has been reached. "
                        "Please try again later or load Presentation Demo."
                    )
                else:
                    st.error(
                        "Chat is temporarily unavailable. Please try again."
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
        download_col5, _ = st.columns(2)

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