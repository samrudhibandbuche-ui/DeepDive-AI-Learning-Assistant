import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"


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


def _validate_flashcards(
    parsed_response: dict,
) -> list[dict]:
    """Validate and format flashcards returned by Gemini."""

    if not isinstance(parsed_response, dict):
        raise ValueError(
            "Gemini returned an invalid flashcard format."
        )

    flashcards = parsed_response.get("flashcards")

    if not isinstance(flashcards, list):
        raise ValueError(
            "Gemini did not return a flashcards list."
        )

    validated_flashcards = []
    seen_fronts = set()

    for card in flashcards:
        if not isinstance(card, dict):
            continue

        front = str(
            card.get("front", "")
        ).strip()

        back = str(
            card.get("back", "")
        ).strip()

        normalized_front = front.lower()

        if not front or not back:
            continue

        if normalized_front in seen_fronts:
            continue

        seen_fronts.add(normalized_front)

        validated_flashcards.append(
            {
                "front": front,
                "back": back,
            }
        )

    if len(validated_flashcards) != 10:
        raise ValueError(
            f"Gemini generated only "
            f"{len(validated_flashcards)} valid flashcards "
            "instead of 10. Please try again."
        )

    return validated_flashcards


def generate_flashcards(
    transcript: str,
) -> list[dict]:
    """Generate exactly ten revision flashcards using Gemini."""

    if not transcript.strip():
        raise ValueError(
            "The transcript is empty."
        )

    if not GEMINI_API_KEY:
        raise ValueError(
            "Gemini API key was not found. "
            "Add GEMINI_API_KEY to the .env file "
            "or Streamlit secrets."
        )

    prompt = f"""
You are DeepDive AI, an educational flashcard-generation assistant.

Create exactly 10 high-quality study flashcards using only the lecture
transcript below.

Requirements:

1. Generate exactly 10 flashcards.
2. Each flashcard must contain:
   - front: a short question, term, or concept.
   - back: a clear and accurate answer.
3. Use only information contained in the transcript.
4. Do not use outside knowledge.
5. Do not repeat flashcards.
6. Cover different important parts of the lecture.
7. Keep the language simple and student-friendly.
8. Make the flashcards useful for revision.
9. Avoid answers that are unnecessarily long.
10. Return the result using the required JSON structure.

LECTURE TRANSCRIPT:

{transcript}
"""

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FLASHCARD_SCHEMA,
            ),
        )

        raw_response = (
            response.text.strip()
            if response.text
            else ""
        )

        if not raw_response:
            raise ValueError(
                "Gemini returned empty flashcard data."
            )

        parsed_response = json.loads(
            raw_response
        )

        return _validate_flashcards(
            parsed_response
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "Gemini returned invalid flashcard data. "
            "Please try again."
        ) from error

    except ValueError:
        raise

    except Exception as error:
        raise RuntimeError(
            f"Flashcard generation failed: {error}"
        ) from error