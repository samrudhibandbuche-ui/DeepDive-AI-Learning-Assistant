import os
import re
from pathlib import Path

import yt_dlp



def sanitize_filename(name: str) -> str:
    """Remove characters that Windows does not allow in filenames."""
    safe_name = re.sub(r'[<>:"/\\|?*]', "", name)
    safe_name = re.sub(r"\s+", " ", safe_name).strip()
    return safe_name[:100] or "YouTube_Video"


def download_youtube_video(
    url: str,
    output_dir: str = "uploads",
) -> tuple[str, str]:
    """
    Download a public YouTube video and return:
    (downloaded_file_path, video_title)
    """

    if not url or not url.strip():
        raise ValueError("Please enter a valid YouTube URL.")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_template = os.path.join(
        output_dir,
        "%(id)s_%(title).80s.%(ext)s",
    )

    ydl_options = {
        # Try separate video/audio first, then fall back to any playable format.
        "format": (
            "bv*+ba/"
            "b[ext=mp4]/"
            "best"
        ),
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        # Merge separate video and audio streams into MP4.
        "merge_output_format": "mp4",

        # Safer filenames for Windows.
        "windowsfilenames": True,

        # Avoid partially downloaded files being treated as complete.
        "continuedl": True,
        "overwrites": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_options) as downloader:
            info = downloader.extract_info(
                url.strip(),
                download=True,
            )

            title = sanitize_filename(
    info.get("title", "YouTube Video")
)

            # yt-dlp provides the final merged path here when available.
            requested_downloads = info.get(
                "requested_downloads",
                [],
            )

            for item in requested_downloads:
                filepath = item.get("filepath")

                if filepath and os.path.exists(filepath):
                    return filepath, title

            prepared_path = downloader.prepare_filename(info)

            possible_paths = [
                prepared_path,
                os.path.splitext(prepared_path)[0] + ".mp4",
                os.path.splitext(prepared_path)[0] + ".mkv",
                os.path.splitext(prepared_path)[0] + ".webm",
            ]

            for possible_path in possible_paths:
                if os.path.exists(possible_path):
                    return possible_path, title

            video_id = info.get("id", "")

            matching_files = list(
                Path(output_dir).glob(f"{video_id}_*")
            )

            valid_extensions = {
                ".mp4",
                ".mkv",
                ".webm",
                ".mov",
            }

            for matching_file in matching_files:
                if (
                    matching_file.is_file()
                    and matching_file.suffix.lower()
                    in valid_extensions
                ):
                    return str(matching_file), title

            raise FileNotFoundError(
                "The video was downloaded, but the final file "
                "could not be located."
            )

    except yt_dlp.utils.DownloadError as error:
        raise ValueError(
            "YouTube could not provide a downloadable format for "
            "this video. Try another public video or update yt-dlp."
        ) from error