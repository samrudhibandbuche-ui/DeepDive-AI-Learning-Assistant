import json
import random
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 10,
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "string"},
                    },
                    "correct_answer": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3,
                    },
                    "explanation": {"type": "string"},
                },
                "required": [
                    "question",
                    "options",
                    "correct_answer",
                    "explanation",
                ],
            },
        }
    },
    "required": ["questions"],
}


def _split_sentences(transcript: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", transcript.strip())

    return [
        sentence.strip()
        for sentence in sentences
        if 30 <= len(sentence.strip()) <= 250
    ]


def _shorten(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())

    if len(text) <= limit:
        return text

    return text[: limit - 3].rstrip() + "..."


def _generate_fallback_quiz(transcript: str) -> list[dict]:
    """
    Generate a simple transcript-based quiz when Ollama is unavailable.

    This fallback uses sentences directly from the transcript, so it does
    not require any external AI service.
    """

    sentences = _split_sentences(transcript)

    if len(sentences) < 4:
        raise ValueError(
            "The transcript is too short to generate a quiz. "
            "Please use a longer video."
        )

    unique_sentences = list(dict.fromkeys(sentences))
    random.shuffle(unique_sentences)

    selected = unique_sentences[:10]

    while len(selected) < 10:
        selected.append(
            unique_sentences[len(selected) % len(unique_sentences)]
        )

    quiz = []

    for index, correct_sentence in enumerate(selected, start=1):
        distractor_pool = [
            sentence
            for sentence in unique_sentences
            if sentence != correct_sentence
        ]

        if len(distractor_pool) >= 3:
            distractors = random.sample(distractor_pool, 3)
        else:
            distractors = distractor_pool[:]

            while len(distractors) < 3:
                distractors.append(
                    "This statement was not explained in the lecture."
                )

        options = [
            _shorten(correct_sentence),
            *[_shorten(item) for item in distractors],
        ]

        random.shuffle(options)

        correct_option = _shorten(correct_sentence)
        correct_answer = options.index(correct_option)

        quiz.append(
            {
                "id": index,
                "question": (
                    "Which statement is supported by the uploaded lecture?"
                ),
                "options": options,
                "correct_answer": correct_answer,
                "explanation": (
                    "The correct option is taken directly from the "
                    "uploaded lecture transcript."
                ),
            }
        )

    return quiz


def _validate_ai_quiz(parsed_quiz: dict) -> list[dict]:
    if not isinstance(parsed_quiz, dict):
        raise ValueError(
            "The generated quiz is not in the expected object format."
        )

    questions = parsed_quiz.get("questions")

    if not isinstance(questions, list):
        raise ValueError(
            "The generated quiz does not contain a questions list."
        )

    validated_quiz = []

    for number, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        explanation = str(item.get("explanation", "")).strip()

        try:
            correct_answer = int(item.get("correct_answer"))
        except (TypeError, ValueError):
            continue

        if not question:
            continue

        if not isinstance(options, list) or len(options) != 4:
            continue

        options = [str(option).strip() for option in options]

        if any(not option for option in options):
            continue

        if correct_answer not in range(4):
            continue

        validated_quiz.append(
            {
                "id": number,
                "question": question,
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation,
            }
        )

    if len(validated_quiz) != 10:
        raise ValueError(
            f"The AI generated only {len(validated_quiz)} valid "
            "questions instead of 10."
        )

    return validated_quiz


def generate_quiz(transcript: str) -> list[dict]:
    """
    Generate ten structured MCQs from a transcript.

    Ollama is used when available. On Streamlit Cloud, where Ollama is
    unavailable, a transcript-based fallback quiz is generated.
    """

    if not transcript.strip():
        raise ValueError("The transcript is empty.")

    prompt = f"""
Create exactly 10 multiple-choice questions based only on the transcript.

Requirements:

- Every question must contain exactly four options.
- correct_answer must be an integer:
  0 means the first option,
  1 means the second option,
  2 means the third option,
  3 means the fourth option.
- Include a short explanation.
- Do not repeat questions.
- Do not use information outside the transcript.
- Keep the wording clear and student-friendly.

TRANSCRIPT:

{transcript}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": QUIZ_SCHEMA,
                "options": {
                    "temperature": 0,
                    "num_ctx": 4096,
                },
            },
            timeout=30,
        )

        response.raise_for_status()

        response_data = response.json()
        raw_quiz = response_data.get("response", "").strip()

        if not raw_quiz:
            return _generate_fallback_quiz(transcript)

        parsed_quiz = json.loads(raw_quiz)
        return _validate_ai_quiz(parsed_quiz)

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        json.JSONDecodeError,
        ValueError,
    ):
        return _generate_fallback_quiz(transcript)