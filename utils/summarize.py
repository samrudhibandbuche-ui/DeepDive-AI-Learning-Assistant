import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"


def generate_study_notes(transcript: str) -> str:
    """Generate structured study notes from a video transcript."""

    if not transcript.strip():
        raise ValueError("The transcript is empty.")

    if not GEMINI_API_KEY:
        raise ValueError(
            "Gemini API key was not found. "
            "Add GEMINI_API_KEY to the .env file."
        )

    prompt = f"""
You are DeepDive AI, an educational note-taking assistant.

Convert the following lecture transcript into clear and accurate study
notes.

Use exactly this structure:

SUMMARY
Write one concise summary paragraph.

DETAILED NOTES
Explain the important concepts using meaningful headings and short
paragraphs.

KEY POINTS
Provide the most important points as bullet points.

KEYWORDS
Provide 8 to 12 important keywords separated by commas.

Rules:

1. Use only information contained in the transcript.
2. Do not add outside information.
3. Use simple, student-friendly language.
4. Remove unnecessary repetition.
5. Keep the notes accurate and useful for revision.

TRANSCRIPT:

{transcript}
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        notes = response.text.strip() if response.text else ""

        if not notes:
            raise ValueError(
                "Gemini returned an empty response."
            )

        return notes

    except Exception as error:
        raise RuntimeError(
            f"Study-note generation failed: {error}"
        ) from error