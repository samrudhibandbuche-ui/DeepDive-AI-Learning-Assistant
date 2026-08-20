import json
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


FLASHCARD_SCHEMA = {
    "type": "object",
    "properties": {
        "flashcards": {
            "type": "array",
            "minItems": 10,
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "front": {"type": "string"},
                    "back": {"type": "string"},
                },
                "required": ["front", "back"],
            },
        },
    },
    "required": ["flashcards"],
}


def _fallback_flashcards(transcript: str):
    """Generate simple flashcards directly from the transcript."""

    sentences = re.split(r"(?<=[.!?])\s+|\n+", transcript.strip())

    sentences = [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 30
    ]

    if len(sentences) < 5:
        raise ValueError(
            "The transcript is too short to generate flashcards."
        )

    flashcards = []

    for sentence in sentences[:10]:
        flashcards.append(
            {
                "front": "Explain the following concept",
                "back": sentence,
            }
        )

    while len(flashcards) < 10:
        flashcards.append(flashcards[-1])

    return flashcards


def generate_flashcards(transcript: str):
    """Generate ten revision flashcards."""

    if not transcript.strip():
        raise ValueError("The transcript is empty.")

    prompt = f"""
Create exactly 10 study flashcards based only on the transcript.

Requirements:

- Each flashcard must contain a short front question or concept.
- Each back must contain a clear and accurate answer.
- Use only information from the transcript.
- Avoid duplicate flashcards.
- Keep the language student-friendly.
- Return valid JSON.

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
                "format": FLASHCARD_SCHEMA,
                "options": {
                    "temperature": 0,
                    "num_ctx": 4096,
                },
            },
            timeout=30,
        )

        response.raise_for_status()

        raw = response.json().get("response", "").strip()

        if not raw:
            return _fallback_flashcards(transcript)

        parsed = json.loads(raw)

        flashcards = parsed.get("flashcards", [])

        valid = []

        for card in flashcards:
            front = str(card.get("front", "")).strip()
            back = str(card.get("back", "")).strip()

            if front and back:
                valid.append(
                    {
                        "front": front,
                        "back": back,
                    }
                )

        if len(valid) != 10:
            return _fallback_flashcards(transcript)

        return valid

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        json.JSONDecodeError,
        ValueError,
    ):
        