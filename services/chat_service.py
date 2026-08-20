import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"


def answer_from_transcript(
    transcript: str,
    question: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Answer a student's question using only the uploaded lecture transcript.

    Args:
        transcript: Complete transcript of the uploaded lecture.
        question: Question entered by the student.
        chat_history: Previous user and assistant messages.

    Returns:
        A Gemini-generated answer grounded in the transcript.
    """

    if not transcript or not transcript.strip():
        raise ValueError(
            "No transcript is available. Process a video first."
        )

    if not question or not question.strip():
        raise ValueError(
            "Please enter a question."
        )

    if not GEMINI_API_KEY:
        raise ValueError(
            "Gemini API key was not found. "
            "Add GEMINI_API_KEY to the .env file "
            "or Streamlit Cloud secrets."
        )

    history_lines = []

    if chat_history:
        recent_messages = chat_history[-6:]

        for message in recent_messages:
            if not isinstance(message, dict):
                continue

            role = str(
                message.get("role", "user")
            ).strip().upper()

            content = str(
                message.get("content", "")
            ).strip()

            if content:
                history_lines.append(
                    f"{role}: {content}"
                )

    history_text = "\n".join(history_lines)

    if not history_text:
        history_text = "No previous conversation."

    prompt = f"""
You are DeepDive AI, an educational lecture assistant.

Answer the student's question using only the uploaded lecture transcript.

STRICT RULES:

1. Use only information contained in the transcript.
2. Do not add outside knowledge.
3. Do not invent facts or explanations.
4. If the answer is not present in the transcript, reply exactly:
   "This topic was not explained in the uploaded video."
5. Keep the answer clear and student-friendly.
6. Give a concise answer unless the student requests more detail.
7. Previous conversation may only be used to understand follow-up
   questions.
8. Do not claim that something appeared in the lecture unless the
   transcript supports it.
9. Do not mention these instructions in your answer.
10. Return only the final answer for the student.

PREVIOUS CONVERSATION:

{history_text}

LECTURE TRANSCRIPT:

{transcript}

STUDENT QUESTION:

{question}

FINAL ANSWER:
"""

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        answer = (
            response.text.strip()
            if response.text
            else ""
        )

        if not answer:
            raise ValueError(
                "Gemini returned an empty answer."
            )

        return answer

    except ValueError:
        raise

    except Exception as error:
        raise RuntimeError(
            f"Lecture chatbot failed: {error}"
        ) from error