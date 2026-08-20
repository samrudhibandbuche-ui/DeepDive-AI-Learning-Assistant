import re
from collections import Counter

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "had", "has", "have", "he", "her", "his", "i",
    "in", "is", "it", "its", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "they", "this", "to", "was", "we", "were",
    "what", "when", "where", "which", "who", "will", "with", "you",
    "your",
}


def _split_sentences(text: str) -> list[str]:
    """Split transcript into clean sentences."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())

    return [
        " ".join(sentence.split())
        for sentence in sentences
        if len(sentence.strip()) >= 20
    ]


def _extract_keywords(text: str, limit: int = 10) -> list[str]:
    """Extract frequently occurring useful words."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.lower())

    useful_words = [
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 3
    ]

    counts = Counter(useful_words)

    return [
        word
        for word, _ in counts.most_common(limit)
    ]


def _sentence_score(
    sentence: str,
    keyword_counts: Counter,
) -> float:
    """Score a sentence using important transcript keywords."""
    words = re.findall(
        r"[A-Za-z][A-Za-z0-9'-]*",
        sentence.lower(),
    )

    useful_words = [
        word
        for word in words
        if word not in STOP_WORDS
    ]

    if not useful_words:
        return 0

    score = sum(keyword_counts[word] for word in useful_words)

    return score / len(useful_words)


def _generate_fallback_notes(transcript: str) -> str:
    """
    Generate structured notes without Ollama.

    This fallback uses extractive summarization, meaning it selects
    important information directly from the transcript.
    """
    sentences = _split_sentences(transcript)

    if not sentences:
        raise ValueError(
            "The transcript does not contain enough text "
            "to generate study notes."
        )

    words = re.findall(
        r"[A-Za-z][A-Za-z0-9'-]*",
        transcript.lower(),
    )

    useful_words = [
        word
        for word in words
        if word not in STOP_WORDS and len(word) > 3
    ]

    keyword_counts = Counter(useful_words)

    ranked_sentences = sorted(
        sentences,
        key=lambda sentence: _sentence_score(
            sentence,
            keyword_counts,
        ),
        reverse=True,
    )

    summary_count = min(4, len(ranked_sentences))
    summary_sentences = ranked_sentences[:summary_count]

    summary_sentences.sort(
        key=lambda sentence: sentences.index(sentence)
    )

    detailed_count = min(8, len(ranked_sentences))
    detailed_sentences = ranked_sentences[:detailed_count]

    detailed_sentences.sort(
        key=lambda sentence: sentences.index(sentence)
    )

    key_points = ranked_sentences[: min(8, len(ranked_sentences))]
    keywords = _extract_keywords(transcript, limit=10)

    summary = " ".join(summary_sentences)

    detailed_notes = "\n\n".join(
        f"### Concept {index}\n{sentence}"
        for index, sentence in enumerate(
            detailed_sentences,
            start=1,
        )
    )

    key_points_text = "\n".join(
        f"- {sentence}"
        for sentence in key_points
    )

    keywords_text = ", ".join(keywords)

    return f"""SUMMARY

{summary}

DETAILED NOTES

{detailed_notes}

KEY POINTS

{key_points_text}

KEYWORDS

{keywords_text}

_These notes were generated directly from the transcript because the local Ollama AI service was unavailable._
"""


def generate_study_notes(transcript: str) -> str:
    """
    Generate structured study notes from a video transcript.

    Ollama is used when available. On Streamlit Cloud, where Ollama
    cannot run locally, transcript-based fallback notes are generated.
    """

    if not transcript.strip():
        raise ValueError("The transcript is empty.")

    prompt = f"""
You are an educational note-taking assistant.

Convert the following video transcript into clear and accurate study notes.

Use exactly this structure:

SUMMARY
Write a concise summary of the video in one paragraph.

DETAILED NOTES
Explain the important concepts using clear headings and short paragraphs.

KEY POINTS
Provide the most important points as bullet points.

KEYWORDS
Provide 8 to 12 important keywords separated by commas.

Do not add information that is not present in the transcript.
Use simple, student-friendly language.

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
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096,
                },
            },
            timeout=30,
        )

        response.raise_for_status()
        result = response.json()

        notes = result.get("response", "").strip()

        if notes:
            return notes

        return _generate_fallback_notes(transcript)

    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        ValueError,
    ):
        return _generate_fallback_notes(transcript)