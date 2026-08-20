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


def _fallback_flashcards(transcript: str) -> list[dict]:
    """Generate simple flashcards directly from the transcript."""

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        transcript.strip(),
    )

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

    for number, sentence in enumerate(sentences[:10], start=1):
        flashcards.append(
            {
                "front": f"Revision concept {number}",
                "back": sentence,
            }
        )

    while len(flashcards) < 10:
        source_card = flashcards[
            len(flashcards) % len(flashcards)
        ]

        flashcards.append(
            {
                "front": f"Revision concept {len(flashcards) + 1}",
                "back": source_card["back"],
            }
        )

    return flashcards


def generate_flashcards(transcript: str) -> list[dict]:
    """Generate ten structured revision flashcards."""

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
- Return the information using the required JSON structure.

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

        raw_response = response.json().get(
            "response",
            "",
        ).strip()

        if not raw_response:
            return _fallback_flashcards(transcript)

        parsed_response = json.loads(raw_response)
        flashcards = parsed_response.get("flashcards", [])

        validated_flashcards = []

        for card in flashcards:
            if not isinstance(card, dict):
                continue

            front = str(card.get("front", "")).strip()
            back = str(card.get("back", "")).strip()

            if front and back:
                validated_flashcards.append(
                    {
                        "front": front,
                        "back": back,
                    }
                )

        if len(validated_flashcards) != 10:
            return _fallback_flashcards(transcript)

        return validated_flashcards

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        json.JSONDecodeError,
        ValueError,
    ):
        return _fallback_flashcards(transcript)