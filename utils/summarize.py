import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


def generate_study_notes(transcript: str) -> str:
    """Generate structured study notes from a video transcript."""

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
            timeout=600,
        )

        response.raise_for_status()
        result = response.json()

        notes = result.get("response", "").strip()

        if not notes:
            raise ValueError("Ollama returned an empty response.")

        return notes

    except requests.exceptions.ConnectionError as error:
        raise ConnectionError(
            "DeepDive AI could not connect to Ollama. "
            "Make sure Ollama is installed and running."
        ) from error

    except requests.exceptions.Timeout as error:
        raise TimeoutError(
            "The AI model took too long to respond. Please try again."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Ollama request failed: {error}"
        ) from error