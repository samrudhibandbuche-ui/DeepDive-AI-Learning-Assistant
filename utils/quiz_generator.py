import json

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
                    "question": {
                        "type": "string"
                    },
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "string"
                        }
                    },
                    "correct_answer": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3
                    },
                    "explanation": {
                        "type": "string"
                    }
                },
                "required": [
                    "question",
                    "options",
                    "correct_answer",
                    "explanation"
                ]
            }
        }
    },
    "required": ["questions"]
}


def generate_quiz(transcript: str) -> list[dict]:
    """Generate ten structured MCQs from a transcript."""

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
            timeout=600,
        )

        response.raise_for_status()

        response_data = response.json()
        raw_quiz = response_data.get("response", "").strip()

        if not raw_quiz:
            raise ValueError("Ollama returned an empty quiz.")

        parsed_quiz = json.loads(raw_quiz)

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

            options = [
                str(option).strip()
                for option in options
            ]

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
                f"The AI generated only "
                f"{len(validated_quiz)} valid questions instead of 10. "
                "Please generate the study material again."
            )

        return validated_quiz

    except json.JSONDecodeError as error:
        raise ValueError(
            "The AI returned invalid JSON. Please try again."
        ) from error

    except requests.exceptions.ConnectionError as error:
        raise ConnectionError(
            "DeepDive AI could not connect to Ollama. "
            "Make sure Ollama is running."
        ) from error

    except requests.exceptions.Timeout as error:
        raise TimeoutError(
            "Quiz generation took too long. Please try again."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Quiz generation failed: {error}"
        ) from error