"""Gemini media analysis service — downloads media from any platform and sends to Gemini."""

import time

from google import genai
from google.genai import types

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError
from brokenclaw.models.gemini import GeminiAnalysis

DEFAULT_MODEL = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    api_key = get_settings().gemini_api_key
    if not api_key:
        raise AuthenticationError(
            "Gemini API key not configured. Get one at "
            "https://aistudio.google.com/apikey and set GEMINI_API_KEY in .env"
        )
    return genai.Client(api_key=api_key)


def _download_media(
    url: str, platform: str | None = None, account: str = "default"
) -> tuple[bytes, str]:
    """Download media and return (bytes, mime_type).

    Dispatches to the appropriate platform's download function for auth,
    or uses plain HTTP for public URLs.
    """
    if platform == "instagram":
        from brokenclaw.services.instagram import download_media
        data, _, mime_type = download_media(url)
        return data, mime_type

    if platform == "linkedin":
        from brokenclaw.services.linkedin import download_attachment
        data, _, mime_type = download_attachment(url, account)
        return data, mime_type

    if platform == "slack":
        # Slack URLs require auth headers — use the slack download client
        from brokenclaw.services.slack_client import slack_download
        from urllib.parse import urlparse
        import mimetypes

        data = slack_download(url, account)
        # Infer mime type from URL
        path = urlparse(url).path
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return data, mime_type

    # Public URL — plain HTTP download
    from curl_cffi import requests as curl_requests

    resp = curl_requests.get(url, impersonate="chrome", allow_redirects=True)
    if resp.status_code >= 400:
        raise IntegrationError(
            f"Media download failed (HTTP {resp.status_code}): {url}"
        )
    mime_type = resp.headers.get("content-type", "application/octet-stream")
    return resp.content, mime_type


def _download_slack_file(
    file_id: str, account: str = "default"
) -> tuple[bytes, str]:
    """Download a Slack file by file_id, return (bytes, mime_type)."""
    from brokenclaw.services.slack import download_file
    data, _, mime_type = download_file(file_id, account)
    return data, mime_type


def _is_video(mime_type: str) -> bool:
    return mime_type.startswith("video/")


def analyze_media(
    media_bytes: bytes,
    mime_type: str,
    prompt: str = "Describe this media in detail.",
    model: str = DEFAULT_MODEL,
) -> GeminiAnalysis:
    """Analyze image or video bytes with Gemini."""
    client = _get_client()
    media_type = "video" if _is_video(mime_type) else "image"

    if media_type == "video":
        # Videos must be uploaded via File API, then referenced in generation
        uploaded_file = client.files.upload(
            file=media_bytes,
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        try:
            # Poll until the file is ACTIVE (processing can take a moment)
            for _ in range(60):
                status = client.files.get(name=uploaded_file.name)
                if status.state == "ACTIVE":
                    break
                time.sleep(2)
            else:
                raise IntegrationError(
                    "Gemini file upload timed out waiting for ACTIVE state"
                )

            response = client.models.generate_content(
                model=model,
                contents=[uploaded_file, prompt],
            )
        finally:
            # Clean up uploaded file
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass  # Best-effort cleanup
    else:
        # Images can be sent inline as bytes
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=media_bytes, mime_type=mime_type),
                prompt,
            ],
        )

    return GeminiAnalysis(
        analysis=response.text,
        model=model,
        media_type=media_type,
    )


def analyze_url(
    url: str,
    prompt: str = "Describe this media in detail.",
    platform: str | None = None,
    account: str = "default",
    model: str = DEFAULT_MODEL,
) -> GeminiAnalysis:
    """Download media from URL and analyze with Gemini."""
    media_bytes, mime_type = _download_media(url, platform, account)
    return analyze_media(media_bytes, mime_type, prompt, model)


def analyze_slack_file(
    file_id: str,
    prompt: str = "Describe this media in detail.",
    account: str = "default",
    model: str = DEFAULT_MODEL,
) -> GeminiAnalysis:
    """Download a Slack file and analyze with Gemini."""
    media_bytes, mime_type = _download_slack_file(file_id, account)
    return analyze_media(media_bytes, mime_type, prompt, model)
