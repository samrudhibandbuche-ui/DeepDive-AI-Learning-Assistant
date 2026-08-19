import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


def answer_from_transcript(
    transcript: str,
    question: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Answer a question using only the uploaded video's transcript.

    Args:
        transcript: Complete transcript of the uploaded video.
        question: User's question.
        chat_history: Previous chat messages.

    Returns:
        AI-generated answer grounded in the transcript.
    """

    if not transcript.strip():
        raise ValueError(
            "No transcript is available. Process a video first."
        )

    if not question.strip():
        raise ValueError("Please enter a question.")

    history_text = ""

    if chat_history:
        recent_messages = chat_history[-6:]

        for message in recent_messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            history_text += f"{role.upper()}: {content}\n"

    prompt = f"""
You are DeepDive AI, an educational assistant.

Your task is to answer the student's question using only the provided
video transcript.

STRICT RULES:

1. Use only information contained in the transcript.
2. Do not use outside knowledge.
3. If the answer is not present in the transcript, say:
   "This topic was not explained in the uploaded video."
4. Keep the answer clear and student-friendly.
5. Give a concise answer unless the student asks for detail.
6. Do not claim that something was stated in the video unless it is
   supported by the transcript.
7. Use previous conversation only to understand follow-up questions.

PREVIOUS CONVERSATION:

{history_text if history_text else "No previous conversation."}

VIDEO TRANSCRIPT:

{transcript}

STUDENT QUESTION:

{question}

ANSWER:
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 8192,
                },
            },
            timeout=600,
        )

        response.raise_for_status()

        result = response.json()
        answer = result.get("response", "").strip()

        if not answer:
            raise ValueError(
                "Ollama returned an empty answer."
            )

        return answer

    except requests.exceptions.ConnectionError as error:
        raise ConnectionError(
            "DeepDive AI could not connect to Ollama. "
            "Make sure Ollama is running."
        ) from error

    except requests.exceptions.Timeout as error:
        raise TimeoutError(
            "The chatbot took too long to respond. Please try again."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Chat request failed: {error}"
        ) from error