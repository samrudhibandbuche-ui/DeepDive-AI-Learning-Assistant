import json

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
                    "front": {
                        "type": "string",
                    },
                    "back": {
                        "type": "string",
                    },
                },
                "required": [
                    "front",
                    "back",
                ],
            },
        },
    },
    "required": [
        "flashcards",
    ],
}


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
            timeout=600,
        )

        response.raise_for_status()

        raw_response = response.json().get(
            "response",
            "",
        ).strip()

        if not raw_response:
            raise ValueError(
                "Ollama returned empty flashcards."
            )

        parsed_response = json.loads(raw_response)

        flashcards = parsed_response.get("flashcards")

        if not isinstance(flashcards, list):
            raise ValueError(
                "The generated flashcards are not in the expected format."
            )

        validated_flashcards = []

        for card in flashcards:
            if not isinstance(card, dict):
                continue

            front = str(card.get("front", "")).strip()
            back = str(card.get("back", "")).strip()

            if not front or not back:
                continue

            validated_flashcards.append(
                {
                    "front": front,
                    "back": back,
                }
            )

        if len(validated_flashcards) != 10:
            raise ValueError(
                f"The AI generated only "
                f"{len(validated_flashcards)} valid flashcards "
                "instead of 10. Please try again."
            )

        return validated_flashcards

    except json.JSONDecodeError as error:
        raise ValueError(
            "The AI returned invalid flashcard data. Please try again."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise ConnectionError(
            "DeepDive AI could not connect to Ollama."
        ) from error

    except requests.exceptions.Timeout as error:
        raise TimeoutError(
            "Flashcard generation took too long."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Flashcard generation failed: {error}"
        ) from error