import json
import os
import time
from pathlib import Path

from utils.extract_audio import extract_audio
from utils.flashcards import generate_flashcards
from utils.pdf_generator import generate_notes_pdf
from utils.quiz_generator import generate_quiz
from utils.summarize import generate_study_notes
from utils.transcribe import transcribe_audio


def create_quiz_text(quiz: list[dict]) -> str:
    """Convert structured quiz questions into downloadable text."""

    lines = []
    option_letters = ["A", "B", "C", "D"]

    for number, item in enumerate(quiz, start=1):
        lines.append(f"Question {number}")
        lines.append(item["question"])
        lines.append("")

        for index, option in enumerate(item["options"]):
            lines.append(f"{option_letters[index]}. {option}")

        correct_index = item["correct_answer"]

        lines.append("")
        lines.append(
            f"Correct Answer: "
            f"{option_letters[correct_index]}. "
            f"{item['options'][correct_index]}"
        )

        if item.get("explanation"):
            lines.append(f"Explanation: {item['explanation']}")

        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    return "\n".join(lines)


def create_flashcards_text(flashcards: list[dict]) -> str:
    """Convert flashcards into downloadable text."""

    lines = []

    for number, card in enumerate(flashcards, start=1):
        lines.append(f"Flashcard {number}")
        lines.append(f"Front: {card['front']}")
        lines.append(f"Back: {card['back']}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    return "\n".join(lines)


def process_video(
    video_path: str,
    video_name: str,
    status_callback=None,
    progress_callback=None,
) -> dict:
    """
    Process an uploaded video and generate all learning material.

    Returns:
        Dictionary containing transcript, notes, quiz, flashcards,
        audio path, PDF path and processing details.
    """

    start_time = time.time()

    Path("notes").mkdir(exist_ok=True)
    Path("quizzes").mkdir(exist_ok=True)
    Path("flashcards").mkdir(exist_ok=True)
    Path("pdfs").mkdir(exist_ok=True)

    video_stem = Path(video_name).stem

    def update_status(message: str, progress: int) -> None:
        if status_callback:
            status_callback(message)

        if progress_callback:
            progress_callback(progress)

    # Step 1: Audio extraction
    update_status(
        "Step 1 of 6: Extracting audio from the video...",
        10,
    )

    audio_path = extract_audio(video_path)

    # Step 2: Transcription
    update_status(
        "Step 2 of 6: Generating transcript with Whisper...",
        30,
    )

    transcript, transcript_file = transcribe_audio(audio_path)

    # Step 3: Study notes
    update_status(
        "Step 3 of 6: Generating AI study notes...",
        50,
    )

    study_notes = generate_study_notes(transcript)

    notes_filename = f"{video_stem}_notes.txt"
    notes_path = os.path.join("notes", notes_filename)

    with open(notes_path, "w", encoding="utf-8") as notes_file:
        notes_file.write(study_notes)

    # Step 4: Interactive quiz
    update_status(
        "Step 4 of 6: Generating interactive quiz...",
        68,
    )

    quiz = generate_quiz(transcript)
    quiz_text = create_quiz_text(quiz)

    quiz_path = os.path.join(
        "quizzes",
        f"{video_stem}_quiz.txt",
    )

    with open(quiz_path, "w", encoding="utf-8") as quiz_file:
        quiz_file.write(quiz_text)

    quiz_json_path = os.path.join(
        "quizzes",
        f"{video_stem}_quiz.json",
    )

    with open(
        quiz_json_path,
        "w",
        encoding="utf-8",
    ) as quiz_json_file:
        json.dump(
            quiz,
            quiz_json_file,
            indent=4,
            ensure_ascii=False,
        )

    # Step 5: Flashcards
    update_status(
        "Step 5 of 6: Generating revision flashcards...",
        84,
    )

    flashcards = generate_flashcards(transcript)
    flashcards_text = create_flashcards_text(flashcards)

    flashcards_path = os.path.join(
        "flashcards",
        f"{video_stem}_flashcards.txt",
    )

    with open(
        flashcards_path,
        "w",
        encoding="utf-8",
    ) as flashcards_file:
        flashcards_file.write(flashcards_text)

    flashcards_json_path = os.path.join(
        "flashcards",
        f"{video_stem}_flashcards.json",
    )

    with open(
        flashcards_json_path,
        "w",
        encoding="utf-8",
    ) as flashcards_json_file:
        json.dump(
            flashcards,
            flashcards_json_file,
            indent=4,
            ensure_ascii=False,
        )

    # Step 6: PDF
    update_status(
        "Step 6 of 6: Creating PDF notes...",
        94,
    )

    pdf_path = generate_notes_pdf(
        video_name=video_name,
        transcript=transcript,
        study_notes=study_notes,
    )

    processing_time = time.time() - start_time

    update_status(
        "Processing completed successfully!",
        100,
    )

    return {
        "transcript": transcript,
        "study_notes": study_notes,
        "quiz": quiz,
        "quiz_text": quiz_text,
        "flashcards": flashcards,
        "flashcards_text": flashcards_text,
        "transcript_file": transcript_file,
        "notes_path": notes_path,
        "quiz_path": quiz_path,
        "flashcards_path": flashcards_path,
        "pdf_path": pdf_path,
        "audio_path": audio_path,
        "video_name": video_name,
        "processing_time": processing_time,
    }