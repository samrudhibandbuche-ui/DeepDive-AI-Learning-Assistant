"""Offline presentation data for Deep Dive's API-free Demo Mode."""

import time
from pathlib import Path

from utils.pdf_generator import generate_notes_pdf


DEMO_TRANSCRIPT = """Python is a high-level, interpreted programming language known for its clear and readable syntax. It was created by Guido van Rossum and first released in 1991.

Python is popular because it is beginner-friendly, open source, and supported by a large community. Instead of compiling an entire program before execution, the Python interpreter runs the program through the Python runtime.

Variables store values such as text, numbers, and Boolean data. Common built-in data types include strings, integers, floating-point numbers, lists, tuples, dictionaries, and sets.

Python uses indentation to define blocks of code. Conditional statements such as if, elif, and else support decision-making. For loops and while loops repeat instructions. Functions organize reusable logic and are created using the def keyword.

Python is used in web development, automation, data analysis, artificial intelligence, machine learning, scientific computing, and software testing. Its extensive library ecosystem helps developers build applications quickly.

A simple Python program can display output using the print function. Good Python programs use meaningful names, small reusable functions, comments where necessary, and appropriate error handling."""


DEMO_NOTES = """## Summary

Python is a readable, high-level programming language used across software development, automation, data analysis and artificial intelligence.

## Detailed Notes

### 1. Python basics
- Python is interpreted, open source and beginner-friendly.
- Guido van Rossum created Python, which was first released in 1991.
- Indentation defines code blocks.

### 2. Core building blocks
- Variables store values.
- Common data types include strings, integers, floats, lists, tuples, dictionaries and sets.
- `if`, `elif` and `else` control decisions.
- `for` and `while` loops repeat instructions.
- Functions are defined with the `def` keyword.

### 3. Applications
- Web development and automation
- Data analysis and scientific computing
- Artificial intelligence and machine learning
- Software testing

## Key Takeaway

Python combines simple syntax with a large library ecosystem, allowing beginners and professionals to build useful applications quickly."""


DEMO_QUIZ = [
    {
        "id": 1,
        "question": "What type of programming language is Python?",
        "options": ["High-level interpreted", "Low-level compiled", "Markup", "Database query"],
        "correct_answer": 0,
        "explanation": "The lecture describes Python as a high-level, interpreted language.",
    },
    {
        "id": 2,
        "question": "Who created Python?",
        "options": ["James Gosling", "Dennis Ritchie", "Guido van Rossum", "Bjarne Stroustrup"],
        "correct_answer": 2,
        "explanation": "Python was created by Guido van Rossum.",
    },
    {
        "id": 3,
        "question": "What does Python use to define code blocks?",
        "options": ["Brackets", "Indentation", "Semicolons", "XML tags"],
        "correct_answer": 1,
        "explanation": "Python uses indentation to define blocks of code.",
    },
    {
        "id": 4,
        "question": "Which keyword is used to define a function?",
        "options": ["func", "method", "define", "def"],
        "correct_answer": 3,
        "explanation": "Python functions are created with the def keyword.",
    },
    {
        "id": 5,
        "question": "Which is an application of Python mentioned in the lesson?",
        "options": ["AI and machine learning", "Only hardware design", "Only word processing", "None of these"],
        "correct_answer": 0,
        "explanation": "The lesson lists AI and machine learning among Python's applications.",
    },
]


DEMO_FLASHCARDS = [
    {"front": "What is Python?", "back": "A high-level, interpreted programming language known for readable syntax."},
    {"front": "Who created Python?", "back": "Guido van Rossum."},
    {"front": "How does Python define code blocks?", "back": "Using indentation."},
    {"front": "Which keyword defines a function?", "back": "The def keyword."},
    {"front": "Name three Python applications.", "back": "Examples include web development, automation, data analysis, AI and machine learning."},
]


def _quiz_text() -> str:
    letters = ["A", "B", "C", "D"]
    blocks = []
    for number, item in enumerate(DEMO_QUIZ, start=1):
        blocks.extend([f"Question {number}", item["question"]])
        blocks.extend(
            f"{letters[index]}. {option}"
            for index, option in enumerate(item["options"])
        )
        correct = item["correct_answer"]
        blocks.extend([
            f"Correct Answer: {letters[correct]}. {item['options'][correct]}",
            f"Explanation: {item['explanation']}",
            "",
        ])
    return "\n".join(blocks)


def _flashcards_text() -> str:
    return "\n\n".join(
        f"Flashcard {number}\nFront: {card['front']}\nBack: {card['back']}"
        for number, card in enumerate(DEMO_FLASHCARDS, start=1)
    )


def get_demo_results(status_callback=None, progress_callback=None) -> dict:
    """Create a complete learning pack locally without any API requests."""

    if status_callback:
        status_callback("Loading the offline presentation learning pack...")
    if progress_callback:
        progress_callback(35)

    output_dir = Path("demo_outputs")
    output_dir.mkdir(exist_ok=True)

    transcript_path = output_dir / "python_basics_transcript.txt"
    notes_path = output_dir / "python_basics_notes.txt"
    quiz_path = output_dir / "python_basics_quiz.txt"
    flashcards_path = output_dir / "python_basics_flashcards.txt"

    quiz_text = _quiz_text()
    flashcards_text = _flashcards_text()

    transcript_path.write_text(DEMO_TRANSCRIPT, encoding="utf-8")
    notes_path.write_text(DEMO_NOTES, encoding="utf-8")
    quiz_path.write_text(quiz_text, encoding="utf-8")
    flashcards_path.write_text(flashcards_text, encoding="utf-8")

    if progress_callback:
        progress_callback(75)

    pdf_path = generate_notes_pdf(
        video_name="Python Basics Demo.mp4",
        transcript=DEMO_TRANSCRIPT,
        study_notes=DEMO_NOTES,
    )

    time.sleep(0.25)
    if progress_callback:
        progress_callback(100)
    if status_callback:
        status_callback("Offline presentation demo is ready!")

    return {
        "transcript": DEMO_TRANSCRIPT,
        "study_notes": DEMO_NOTES,
        "quiz": DEMO_QUIZ,
        "quiz_text": quiz_text,
        "flashcards": DEMO_FLASHCARDS,
        "flashcards_text": flashcards_text,
        "transcript_file": str(transcript_path),
        "notes_path": str(notes_path),
        "quiz_path": str(quiz_path),
        "flashcards_path": str(flashcards_path),
        "pdf_path": pdf_path,
        "audio_path": "",
        "video_name": "Python Basics Demo.mp4",
        "processing_time": 0.25,
        "demo_mode": True,
    }


def answer_demo_question(question: str) -> str:
    """Answer common demo questions locally from the sample transcript."""

    normalized = question.lower().strip()

    if not normalized:
        raise ValueError("Please enter a question.")

    if "what is python" in normalized or "define python" in normalized:
        return "Python is a high-level, interpreted programming language known for its clear and readable syntax."
    if "who" in normalized and ("create" in normalized or "develop" in normalized):
        return "Python was created by Guido van Rossum and was first released in 1991."
    if "application" in normalized or "used for" in normalized or "uses" in normalized:
        return "The lecture mentions web development, automation, data analysis, AI, machine learning, scientific computing and software testing."
    if "function" in normalized or "def" in normalized:
        return "Functions organize reusable logic in Python and are created using the def keyword."
    if "indent" in normalized or "block" in normalized:
        return "Python uses indentation to define blocks of code."
    if "data type" in normalized or "list" in normalized:
        return "The lecture mentions strings, integers, floating-point numbers, lists, tuples, dictionaries and sets."
    if "summary" in normalized or "main idea" in normalized:
        return "Python is a readable and beginner-friendly language with a large library ecosystem, making it useful for many kinds of software and AI projects."

    return "This topic was not explained in the uploaded video."
