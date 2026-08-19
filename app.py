import os
from pathlib import Path

import streamlit as st

from services.chat_service import answer_from_transcript
from services.processing_service import process_video
from utils.helpers import create_directories


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="DeepDive AI",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown(
    """
    <style>
        .main-title {
            font-size: 46px;
            font-weight: 800;
            margin-bottom: 0;
        }

        .main-subtitle {
            font-size: 18px;
            opacity: 0.75;
            margin-top: 0;
            margin-bottom: 25px;
        }

        .feature-card {
            padding: 18px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
            margin-bottom: 12px;
            min-height: 145px;
        }

        .status-card {
            padding: 16px;
            border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            margin-top: 12px;
        }

        .flashcard {
            padding: 35px;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 18px;
            min-height: 230px;
            text-align: center;
            margin: 20px 0;
        }

        .flashcard-label {
            font-size: 14px;
            opacity: 0.65;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .flashcard-content {
            font-size: 24px;
            font-weight: 600;
            margin-top: 20px;
            line-height: 1.5;
        }

        .small-text {
            font-size: 14px;
            opacity: 0.75;
        }

        div.stButton > button {
            width: 100%;
            border-radius: 10px;
            font-weight: 600;
        }

        div.stDownloadButton > button {
            width: 100%;
            border-radius: 10px;
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


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("🎥 DeepDive AI")
    st.caption("AI-Powered Learning Assistant")

    st.divider()

    st.write("### Processing Pipeline")
    st.write("1. 📤 Upload lecture video")
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
    st.write("- Whisper")
    st.write("- Ollama")
    st.write("- Llama 3.2")
    st.write("- MoviePy")
    st.write("- FFmpeg")
    st.write("- ReportLab")

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
    '<p class="main-title">DeepDive AI</p>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p class="main-subtitle">
        Transform lecture videos into transcripts, structured notes,
        interactive quizzes, flashcards and an intelligent lecture chatbot.
    </p>
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
            <h4>🎙️ Transcription</h4>
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
            <h4>🧠 Study Material</h4>
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
            <h4>❓ Quiz & Flashcards</h4>
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
            <h4>💬 Lecture Chat</h4>
            <p class="small-text">
                Answers questions using only the uploaded lecture transcript.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.divider()


# =========================================================
# VIDEO UPLOAD
# =========================================================
st.write("## 📤 Upload Lecture Video")

uploaded_video = st.file_uploader(
    "Choose a video file",
    type=["mp4", "mov", "avi", "mkv"],
    help="Use a short MP4 video while testing.",
    key="lecture_video_uploader",
)


if uploaded_video is not None:
    save_path = os.path.join(
        "uploads",
        uploaded_video.name,
    )

    with open(save_path, "wb") as video_file:
        video_file.write(uploaded_video.getbuffer())

    video_column, information_column = st.columns([2, 1])

    with video_column:
        st.write("### Video Preview")
        st.video(save_path)

    with information_column:
        st.write("### Video Information")

        file_size_mb = uploaded_video.size / (1024 * 1024)

        st.markdown(
            f"""
            <div class="status-card">
                <b>File name</b><br>
                {uploaded_video.name}<br><br>

                <b>File size</b><br>
                {file_size_mb:.2f} MB<br><br>

                <b>Status</b><br>
                Ready for processing
            </div>
            """,
            unsafe_allow_html=True,
        )

        generate_clicked = st.button(
            "🚀 Generate Study Material",
            type="primary",
            key="generate_material_button",
        )

    if generate_clicked:
        progress_bar = st.progress(0)
        status_message = st.empty()

        def update_status(message: str) -> None:
            status_message.info(message)

        def update_progress(progress: int) -> None:
            progress_bar.progress(progress)

        try:
            results = process_video(
                video_path=save_path,
                video_name=uploaded_video.name,
                status_callback=update_status,
                progress_callback=update_progress,
            )

            st.session_state.processed = True
            st.session_state.transcript = results["transcript"]
            st.session_state.study_notes = results["study_notes"]
            st.session_state.quiz = results["quiz"]
            st.session_state.quiz_text = results["quiz_text"]
            st.session_state.flashcards = results["flashcards"]
            st.session_state.flashcards_text = results[
                "flashcards_text"
            ]

            st.session_state.transcript_file = results[
                "transcript_file"
            ]
            st.session_state.notes_path = results["notes_path"]
            st.session_state.quiz_path = results["quiz_path"]
            st.session_state.flashcards_path = results[
                "flashcards_path"
            ]
            st.session_state.pdf_path = results["pdf_path"]
            st.session_state.audio_path = results["audio_path"]
            st.session_state.video_name = results["video_name"]
            st.session_state.processing_time = results[
                "processing_time"
            ]

            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.flashcard_index = 0
            st.session_state.flashcard_revealed = False
            st.session_state.chat_messages = []

            progress_bar.progress(100)

            status_message.success(
                "All study material generated successfully!"
            )

        except ValueError as error:
            progress_bar.empty()
            status_message.empty()
            st.error(str(error))

        except ConnectionError as error:
            progress_bar.empty()
            status_message.empty()

            st.error(str(error))

            st.info(
                "Make sure Ollama is running. Open Ollama or run "
                "`ollama serve` in another terminal."
            )

        except TimeoutError as error:
            progress_bar.empty()
            status_message.empty()
            st.error(str(error))

        except Exception as error:
            progress_bar.empty()
            status_message.empty()
            st.error(f"Processing failed: {error}")

else:
    st.info("Upload an MP4, MOV, AVI or MKV video to begin.")


# =========================================================
# RESULTS DASHBOARD
# =========================================================
if st.session_state.processed:
    st.divider()

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
            "💬 Chat with Video",
            "🎵 Audio",
            "📥 Downloads",
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
                "Submit Quiz",
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
                label="Download Flashcards",
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
            st.write("### 💬 Ask Questions About the Lecture")
            st.caption(
                "DeepDive AI will answer using only the uploaded video transcript."
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
            "Ask a question about the uploaded lecture...",
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
                        "DeepDive AI is checking the lecture..."
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
                st.info(
                    "Make sure Ollama is running."
                )

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
        download_col5, _ = st.columns(2)

        with download_col1:
            st.download_button(
                label="Download Transcript",
                data=st.session_state.transcript,
                file_name=f"{video_stem}_transcript.txt",
                mime="text/plain",
                key="download_transcript_downloads_tab",
            )

        with download_col2:
            st.download_button(
                label="Download Study Notes",
                data=st.session_state.study_notes,
                file_name=f"{video_stem}_notes.txt",
                mime="text/plain",
                key="download_notes_downloads_tab",
            )

        with download_col3:
            st.download_button(
                label="Download Quiz with Answers",
                data=st.session_state.quiz_text,
                file_name=f"{video_stem}_quiz.txt",
                mime="text/plain",
                key="download_quiz_downloads_tab",
            )

        with download_col4:
            st.download_button(
                label="Download Flashcards",
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
                    label="Download PDF Notes",
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