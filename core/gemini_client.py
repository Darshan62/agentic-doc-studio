"""
Small Gemini REST client built on the standard library (no SDK needed).
"""
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1"
DEFAULT_MODEL = "gemini-3.5-flash"  # gemini-2.5-flash is retired for new keys (HTTP 404)
# Tried in order when a model is retired (404), out of quota (429, free-tier quotas are per model) or overloaded (503)
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
RETRY_STATUS = (404, 429, 503)
JSON_ATTEMPTS = 2
TIMEOUT_SECONDS = 120

# urllib tries IPv6 addresses first and waits for each one to time out. On networks with
# broken IPv6 that makes every Gemini call hang for minutes, so resolve to IPv4 only.
_system_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, *args, **kwargs):
    return _system_getaddrinfo(host, port, socket.AF_INET, *args, **kwargs)


socket.getaddrinfo = _ipv4_getaddrinfo


class GeminiError(Exception):
    pass


KEY_HELP = "Create a Gemini API key at https://aistudio.google.com/apikey, set GEMINI_API_KEY in .env and restart the server."


def _error_reason(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read() or b"{}").get("error", {}).get("status", "") or ""
    except (ValueError, OSError, AttributeError):
        return ""


def describe_http_error(e: urllib.error.HTTPError) -> str:
    """Turns Gemini's HTTP status into a message that says what to do. Keeps the code for debugging."""
    reason = _error_reason(e)
    if e.code == 401 or (e.code == 400 and reason in ("INVALID_ARGUMENT", "")):
        return f"Gemini rejected GEMINI_API_KEY (HTTP {e.code}): it is invalid, expired or not a Gemini API key. {KEY_HELP}"
    if e.code == 403:
        return (f"Gemini refused the request (HTTP 403): the key's project can't use the Gemini API "
                f"(API not enabled or key restricted). {KEY_HELP}")
    if e.code == 404:
        return f"Gemini model '{os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)}' was not found (HTTP 404). Check GEMINI_MODEL in .env."
    if e.code == 429:
        return "Gemini quota or rate limit reached (HTTP 429). Wait a minute and try again, or use a key with more quota."
    if e.code >= 500:
        return f"Gemini is temporarily unavailable (HTTP {e.code}). Please try again shortly."
    return f"Gemini request failed with HTTP {e.code}{f' ({reason})' if reason else ''}."


def check_api_key(timeout: int = 8) -> str:
    """Cheap key check (lists one model, no tokens used): 'ok' | 'missing' | 'invalid' | 'unreachable'."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "MY_GEMINI_API_KEY":
        return "missing"
    request = urllib.request.Request(MODELS_URL, headers={"x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return "ok"
    except urllib.error.HTTPError as e:
        return "invalid" if e.code in (400, 401, 403) else "unreachable"
    except (urllib.error.URLError, TimeoutError, socket.timeout):
        return "unreachable"


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

    models = [model] + [m for m in FALLBACK_MODELS if m != model]
    try:
        data = _post_with_fallback(models, body, api_key, timeout)
    except urllib.error.URLError as e:
        raise GeminiError(f"Could not reach Gemini: {e.reason}") from e
    except (TimeoutError, socket.timeout) as e:
        raise GeminiError(f"Gemini did not answer within {timeout} seconds.") from e

    candidate = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
    if not text:
        raise GeminiError("Gemini returned an empty answer.")
    if candidate.get("finishReason") == "MAX_TOKENS":
        print(f"[gemini] answer cut off at the output token limit ({len(text)} chars)", file=sys.stderr)

    sources = []
    for chunk in candidate.get("groundingMetadata", {}).get("groundingChunks", []):
        web = chunk.get("web")
        if web:
            sources.append({"title": web.get("title", ""), "url": web.get("uri", "")})
    return text, sources


def _post_with_fallback(models: List[str], body: Dict[str, Any], api_key: str, timeout: int) -> Dict[str, Any]:
    """Posts to each model in turn; moves on only when a model is retired, out of quota or overloaded."""
    for index, model in enumerate(models):
        request = urllib.request.Request(
            API_URL.format(model=model),
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except json.JSONDecodeError as e:
            raise GeminiError("Gemini returned an unreadable response. Please try again.") from e
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUS and index < len(models) - 1:
                continue
            raise GeminiError(describe_http_error(e)) from e
    raise GeminiError("No Gemini model is configured.")


def parse_json_answer(text: str) -> Dict[str, Any]:
    """Parses a JSON answer, tolerating ```json fences or a sentence before/after the object."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start:end + 1])


def ask_gemini_json(prompt: str, timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> Dict[str, Any]:
    # Gemini occasionally returns broken JSON (e.g. an answer cut off mid-object), so ask once more
    for attempt in range(JSON_ATTEMPTS):
        text, _ = ask_gemini(prompt, want_json=True, timeout=timeout, fast=fast)
        try:
            answer = parse_json_answer(text)
            if isinstance(answer, dict):
                return answer
        except json.JSONDecodeError as e:
            print(f"[gemini] attempt {attempt + 1}: invalid JSON ({e.msg} at {e.pos}/{len(text)} chars): "
                  f"...{text[max(0, e.pos - 80):e.pos + 40]!r}", file=sys.stderr)
    raise GeminiError("Gemini did not return valid JSON twice in a row. Please try again.")
