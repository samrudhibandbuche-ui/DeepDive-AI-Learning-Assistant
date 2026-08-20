import re
from collections import Counter

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "how", "i", "in", "is", "it", "of", "on", "or",
    "that", "the", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "will", "with", "you", "your",
}


def _clean_words(text: str) -> list[str]:
    """Convert text into useful lowercase words."""
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def _answer_using_transcript_search(
    transcript: str,
    question: str,
) -> str:
    """
    Create a simple answer by selecting transcript sentences
    that best match the question.
    """

    question_words = Counter(_clean_words(question))

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        transcript.strip(),
    )

    scored_sentences = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) < 15:
            continue

        sentence_words = Counter(_clean_words(sentence))

        score = sum(
            min(question_words[word], sentence_words[word])
            for word in question_words
        )

        if score > 0:
            scored_sentences.append((score, sentence))

    if not scored_sentences:
        return (
            "This topic was not clearly explained in the uploaded video."
        )

    scored_sentences.sort(key=lambda item: item[0], reverse=True)

    selected_sentences = []
    seen = set()

    for _, sentence in scored_sentences:
        normalized = sentence.lower()

        if normalized not in seen:
            selected_sentences.append(sentence)
            seen.add(normalized)

        if len(selected_sentences) == 3:
            break

    answer = " ".join(selected_sentences)

    return (
        f"{answer}\n\n"
        "_Answer generated directly from the transcript because the "
        "Ollama AI service is unavailable._"
    )


def answer_from_transcript(
    transcript: str,
    question: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Answer a question using only the uploaded video's transcript.

    Ollama is used when available. If Ollama is unavailable, the
    application automatically uses transcript-based sentence matching.
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

Answer the student's question using only the provided video transcript.

STRICT RULES:

1. Use only information contained in the transcript.
2. Do not use outside knowledge.
3. If the answer is not present, say:
   "This topic was not explained in the uploaded video."
4. Keep the answer clear and student-friendly.
5. Give a concise answer unless detail is requested.
6. Use previous conversation only for follow-up context.

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
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()
        answer = result.get("response", "").strip()

        if answer:
            return answer

        return _answer_using_transcript_search(
            transcript,
            question,
        )

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        ValueError,
    ):
        return _answer_using_transcript_search(
            transcript,
            question,
        )