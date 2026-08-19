import os


def create_directories():
    folders = [
        "uploads",
        "audio",
        "transcripts",
        "notes"
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)