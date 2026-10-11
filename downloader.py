from pathlib import Path
from typing import Any

import yt_dlp as ytdlp

from UI.settings import get_download_directory


BASE_DIR = Path(__file__).resolve().parent


def get_download_folder() -> Path:
    """Return the configured download folder, creating it when necessary."""
    folder = get_download_directory()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _base_options(create_download_folder: bool = True) -> dict[str, Any]:
    output_folder = (
        get_download_folder()
        if create_download_folder
        else get_download_directory()
    )
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": str(output_folder / "%(title)s.%(ext)s"),
        "windowsfilenames": True,
    }
    ffmpeg_folder = BASE_DIR / "ffmpeg" / "windows"
    if ffmpeg_folder.is_dir():
        options["ffmpeg_location"] = str(ffmpeg_folder)
    return options


def _extract_video_data(url: str) -> dict[str, Any]:
    url = url.strip()
    if not url:
        raise ValueError("Vui lòng nhập link video.")

    options = _base_options(create_download_folder=False)
    options["skip_download"] = True
    with ytdlp.YoutubeDL(options) as ydl:
        info_dict = ydl.extract_info(url, download=False)
    if not info_dict:
        raise ytdlp.utils.DownloadError("Không lấy được thông tin video.")
    return info_dict


def _metadata(info_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "thumbnail": info_dict.get("thumbnail"),
        "title": info_dict.get("title"),
        "duration": info_dict.get("duration"),
        "author": info_dict.get("uploader") or info_dict.get("channel") or info_dict.get("creator"),
    }


def _formats(
    info_dict: dict[str, Any],
) -> tuple[list[str], list[str], list[str], list[str]]:
    video_formats: dict[tuple[Any, ...], dict[str, Any]] = {}
    audio_ids: list[str] = []
    audio_labels: list[str] = []

    for video_format in info_dict.get("formats", []):
        format_id = video_format.get("format_id")
        if not format_id:
            continue

        vcodec = video_format.get("vcodec")
        acodec = video_format.get("acodec")
        ext = video_format.get("ext", "unknown")

        if vcodec and vcodec != "none":
            resolution = video_format.get("resolution")
            if not resolution:
                width = video_format.get("width")
                height = video_format.get("height")
                resolution = f"{width}x{height}" if width and height else "Độ phân giải không rõ"

            width = video_format.get("width")
            height = video_format.get("height")
            resolution_key = (
                ("dimensions", width, height)
                if width and height
                else ("resolution", resolution.casefold())
            )
            format_rank = (
                ext.casefold() == "mp4",
                video_format.get("fps") or 0,
                video_format.get("tbr") or video_format.get("vbr") or 0,
            )
            existing = video_formats.get(resolution_key)
            if existing and existing["rank"] >= format_rank:
                continue

            label = f"{resolution} ({ext})"
            fps = video_format.get("fps")
            if fps:
                label += f", {fps:g} fps"
            if acodec == "none":
                label += ", chỉ video"
            video_formats[resolution_key] = {
                "format_id": format_id,
                "label": label,
                "rank": format_rank,
                "quality": (
                    height or 0,
                    width or 0,
                    *format_rank[1:],
                ),
            }
        elif acodec and acodec != "none":
            audio_ids.append(format_id)
            bitrate = video_format.get("abr")
            label = ext
            if bitrate:
                label += f", {bitrate:g} kbps"
            audio_labels.append(label)

    best_video_formats = sorted(
        video_formats.values(),
        key=lambda video_format: video_format["quality"],
        reverse=True,
    )
    video_ids = [video_format["format_id"] for video_format in best_video_formats]
    video_labels = [video_format["label"] for video_format in best_video_formats]
    return video_ids, video_labels, audio_ids, audio_labels


def get_video_data(url: str) -> dict[str, Any]:
    """Fetch video metadata and available download formats in one extraction."""
    info_dict = _extract_video_data(url)
    video_ids, video_labels, audio_ids, audio_labels = _formats(info_dict)
    return {
        "metadata": _metadata(info_dict),
        "video_formats": list(zip(video_ids, video_labels)),
        "audio_formats": list(zip(audio_ids, audio_labels)),
    }


def info(url: str) -> dict[str, Any]:
    return _metadata(_extract_video_data(url))


def list_formats(url: str) -> tuple[list[str], list[str], list[str], list[str]]:
    return _formats(_extract_video_data(url))


def download_video(url: str, format_id: str | None = None) -> None:
    url = url.strip()
    if not url:
        raise ValueError("Vui lòng nhập link video.")

    options = _base_options()
    options["merge_output_format"] = "mp4"
    if format_id:
        info_dict = _extract_video_data(url)
        selected_format = next(
            (
                video_format
                for video_format in info_dict.get("formats", [])
                if video_format.get("format_id") == format_id
            ),
            None,
        )
        if selected_format is None:
            raise ValueError("Định dạng video đã chọn không còn khả dụng.")
        if selected_format.get("acodec") == "none":
            options["format"] = f"{format_id}+bestaudio/{format_id}"
        else:
            options["format"] = format_id
    else:
        options["format"] = "bestvideo+bestaudio/best"

    with ytdlp.YoutubeDL(options) as ydl:
        ydl.download([url.strip()])


def download_audio(
    url: str,
    format_id: str | None = None,
    quality: str = "192",
) -> None:
    url = url.strip()
    if not url:
        raise ValueError("Vui lòng nhập link video.")

    options = _base_options()
    options["format"] = format_id or "bestaudio/best"
    options["postprocessors"] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality,
        }
    ]

    with ytdlp.YoutubeDL(options) as ydl:
        ydl.download([url])


# Keep the original misspelling available for callers using the old function name.
dowload_video = download_video
