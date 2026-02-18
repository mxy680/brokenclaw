import requests

from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.models.wolfram import WolframPod, WolframResult, WolframShortAnswer

WOLFRAM_API_BASE = "https://api.wolframalpha.com"


def _get_app_id() -> str:
    app_id = get_settings().wolfram_app_id
    if not app_id:
        raise AuthenticationError(
            "Wolfram Alpha AppID not configured. Get one at "
            "https://developer.wolframalpha.com/access and set WOLFRAM_APP_ID in .env"
        )
    return app_id


def query(input_text: str, units: str = "nonmetric") -> WolframResult:
    """Full structured query — returns all result pods with plaintext."""
    resp = requests.get(
        f"{WOLFRAM_API_BASE}/v2/query",
        params={
            "appid": _get_app_id(),
            "input": input_text,
            "output": "json",
            "format": "plaintext",
            "units": units,
        },
    )
    if resp.status_code == 403:
        raise AuthenticationError("Wolfram Alpha AppID is invalid. Check WOLFRAM_APP_ID in .env.")
    if resp.status_code == 429:
        raise RateLimitError("Wolfram Alpha rate limit exceeded.")
    if resp.status_code >= 400:
        raise IntegrationError(f"Wolfram Alpha API error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    qr = data.get("queryresult", {})

    pods = []
    input_interpretation = None
    for pod in qr.get("pods", []):
        title = pod.get("title", "")
        # Collect plaintext from all subpods
        texts = []
        for subpod in pod.get("subpods", []):
            text = subpod.get("plaintext")
            if text:
                texts.append(text)
        combined = "\n".join(texts) if texts else None
        if title == "Input interpretation" or title == "Input":
            input_interpretation = combined
        pods.append(WolframPod(title=title, text=combined))

    return WolframResult(
        input_interpretation=input_interpretation,
        pods=pods,
        success=qr.get("success", False),
    )


def short_answer(input_text: str, units: str = "imperial") -> WolframShortAnswer:
    """Quick one-line answer."""
    resp = requests.get(
        f"{WOLFRAM_API_BASE}/v1/result",
        params={
            "appid": _get_app_id(),
            "i": input_text,
            "units": units,
        },
    )
    if resp.status_code == 403:
        raise AuthenticationError("Wolfram Alpha AppID is invalid. Check WOLFRAM_APP_ID in .env.")
    if resp.status_code == 429:
        raise RateLimitError("Wolfram Alpha rate limit exceeded.")
    if resp.status_code == 501:
        raise IntegrationError(f"Wolfram Alpha could not interpret the query: '{input_text}'")
    if resp.status_code >= 400:
        raise IntegrationError(f"Wolfram Alpha error ({resp.status_code}): {resp.text[:200]}")

    return WolframShortAnswer(query=input_text, answer=resp.text)
