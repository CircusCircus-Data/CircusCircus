"""Validation and embedding helpers for post media links."""

import re
from urllib.parse import parse_qs, urlparse


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_MEDIA_URL_LENGTH = 2048
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
VIMEO_HOSTS = {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIMEO_ID = re.compile(r"^\d+$")


def _https_url(value):
    """Return a parsed HTTPS URL, or None when the URL is unsafe."""

    cleaned = (value or "").strip()
    if len(cleaned) > MAX_MEDIA_URL_LENGTH:
        return None
    try:
        parsed = urlparse(cleaned)
        hostname = parsed.hostname
        username = parsed.username
    except ValueError:
        return None
    if parsed.scheme != "https" or not hostname or username:
        return None
    return parsed


def valid_image_url(value):
    """Accept direct HTTPS links to the supported raster image formats."""

    if not value:
        return True
    parsed = _https_url(value)
    if parsed is None:
        return False
    path = parsed.path.lower()
    return any(path.endswith(extension) for extension in IMAGE_EXTENSIONS)


def video_embed_url(value):
    """Convert an allowlisted YouTube or Vimeo URL to a safe embed URL."""

    if not value:
        return None
    parsed = _https_url(value)
    if parsed is None:
        return None

    host = parsed.hostname.lower()
    parts = [part for part in parsed.path.split("/") if part]
    video_id = None

    if host == "youtu.be" and parts:
        video_id = parts[0]
    elif host in YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif len(parts) >= 2 and parts[0] in {"embed", "shorts"}:
            video_id = parts[1]
        if video_id and YOUTUBE_ID.fullmatch(video_id):
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
        return None

    if host in VIMEO_HOSTS and parts:
        video_id = parts[-1]
        if VIMEO_ID.fullmatch(video_id):
            return f"https://player.vimeo.com/video/{video_id}"

    if video_id and YOUTUBE_ID.fullmatch(video_id):
        return f"https://www.youtube-nocookie.com/embed/{video_id}"
    return None


def valid_video_url(value):
    """Return whether a blank or supported video URL is valid."""

    return not value or video_embed_url(value) is not None
