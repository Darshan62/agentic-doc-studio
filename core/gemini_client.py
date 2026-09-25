"""
Small Gemini REST client built on the standard library (no SDK needed).
"""
import base64
import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
TIMEOUT_SECONDS = 120

# urllib tries IPv6 addresses first and waits for each one to time out. On networks with
# broken IPv6 that makes every Gemini call hang for minutes, so resolve to IPv4 only.
_system_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, *args, **kwargs):
    return _system_getaddrinfo(host, port, socket.AF_INET, *args, **kwargs)


socket.getaddrinfo = _ipv4_getaddrinfo


class GeminiError(Exception):
    pass


def ask_gemini(prompt: str, want_json: bool = False, use_web_search: bool = False,
               image_bytes: Optional[bytes] = None, image_mime: str = "image/png",
               timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> Tuple[str, List[Dict[str, str]]]:
    """Sends one prompt to Gemini. Returns (answer_text, web_sources)."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not set. Add it to your .env file.")

    parts: List[Dict[str, Any]] = [{"text": prompt}]
    if image_bytes:
        parts.append({"inline_data": {"mime_type": image_mime, "data": base64.b64encode(image_bytes).decode()}})

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    body: Dict[str, Any] = {"contents": [{"role": "user", "parts": parts}]}
    config: Dict[str, Any] = {}
    if want_json:
        config["responseMimeType"] = "application/json"
    if fast and "flash" in model:
        # Short structured tasks (edit parsing) don't need "thinking"; it only adds seconds of latency
        config["thinkingConfig"] = {"thinkingBudget": 0}
    if config:
        body["generationConfig"] = config
    if use_web_search:
        body["tools"] = [{"google_search": {}}]

    request = urllib.request.Request(
        API_URL.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        raise GeminiError(f"Gemini request failed with HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise GeminiError(f"Could not reach Gemini: {e.reason}") from e
    except (TimeoutError, socket.timeout) as e:
        raise GeminiError(f"Gemini did not answer within {timeout} seconds.") from e

    candidate = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
    if not text:
        raise GeminiError("Gemini returned an empty answer.")

    sources = []
    for chunk in candidate.get("groundingMetadata", {}).get("groundingChunks", []):
        web = chunk.get("web")
        if web:
            sources.append({"title": web.get("title", ""), "url": web.get("uri", "")})
    return text, sources


def ask_gemini_json(prompt: str, timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> Dict[str, Any]:
    text, _ = ask_gemini(prompt, want_json=True, timeout=timeout, fast=fast)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise GeminiError("Gemini did not return valid JSON.") from e
