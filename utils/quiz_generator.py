import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"


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
                    "question": {
                        "type": "string",
                    },
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "string",
                        },
                    },
                    "correct_answer": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3,
                    },
                    "explanation": {
                        "type": "string",
                    },
                },
                "required": [
                    "question",
                    "options",
                    "correct_answer",
                    "explanation",
                ],
            },
        },
    },
    "required": [
        "questions",
    ],
}


def _validate_quiz(parsed_quiz: dict) -> list[dict]:
    """Validate and format the quiz returned by Gemini."""

    if not isinstance(parsed_quiz, dict):
        raise ValueError(
            "Gemini returned an invalid quiz format."
        )

    questions = parsed_quiz.get("questions")

    if not isinstance(questions, list):
        raise ValueError(
            "Gemini did not return a questions list."
        )

    validated_quiz = []

    for number, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            continue

        question = str(
            item.get("question", "")
        ).strip()

        options = item.get("options", [])

        explanation = str(
            item.get("explanation", "")
        ).strip()

        try:
            correct_answer = int(
                item.get("correct_answer")
            )
        except (TypeError, ValueError):
            continue

        if not question:
            continue

        if not isinstance(options, list):
            continue

        if len(options) != 4:
            continue

        clean_options = [
            str(option).strip()
            for option in options
        ]

        if any(
            not option
            for option in clean_options
        ):
            continue

        if correct_answer not in range(4):
            continue

        validated_quiz.append(
            {
                "id": number,
                "question": question,
                "options": clean_options,
                "correct_answer": correct_answer,
                "explanation": explanation,
            }
        )

    if len(validated_quiz) != 10:
        raise ValueError(
            f"Gemini generated only "
            f"{len(validated_quiz)} valid questions "
            "instead of 10. Please try again."
        )

    return validated_quiz


def generate_quiz(transcript: str) -> list[dict]:
    """Generate exactly ten MCQs using Gemini."""

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
You are DeepDive AI, an educational quiz-generation assistant.

Create exactly 10 multiple-choice questions using only the lecture
transcript below.

Requirements:

1. Generate exactly 10 questions.
2. Every question must contain exactly four options.
3. Only one option should be correct.
4. correct_answer must be an integer:
   0 means the first option,
   1 means the second option,
   2 means the third option,
   3 means the fourth option.
5. Include a short explanation for every correct answer.
6. Do not repeat questions.
7. Do not use information that is not present in the transcript.
8. Keep the language clear and student-friendly.
9. Make the questions useful for revision.
10. Return the result in the required JSON structure.

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
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=QUIZ_SCHEMA,
            ),
        )

        raw_quiz = (
            response.text.strip()
            if response.text
            else ""
        )

        if not raw_quiz:
            raise ValueError(
                "Gemini returned an empty quiz."
            )

        parsed_quiz = json.loads(raw_quiz)

        return _validate_quiz(parsed_quiz)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Gemini returned invalid quiz data. "
            "Please try again."
        ) from error

    except ValueError:
        raise

    except Exception as error:
        raise RuntimeError(
            f"Quiz generation failed: {error}"
        ) from error