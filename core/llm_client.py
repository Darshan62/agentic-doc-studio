"""Provider-neutral LLM client with local Ollama and optional Gemini backends."""
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_VISION_MODEL = "qwen3-vl:8b"
DEFAULT_CONTEXT_SIZE = 8192
TIMEOUT_SECONDS = 300
JSON_ATTEMPTS = 2
SUPPORTED_PROVIDERS = ("ollama", "gemini")


class LLMError(Exception):
    """A provider-independent error safe to show to the user."""


def provider_name() -> str:
    provider = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMError(
            f"Unsupported AI_PROVIDER '{provider}'. Choose one of: {', '.join(SUPPORTED_PROVIDERS)}."
        )
    return provider


def provider_label() -> str:
    return "Ollama" if provider_name() == "ollama" else "Gemini"


def provider_is_configured() -> bool:
    if provider_name() == "ollama":
        return True
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return bool(key and key != "MY_GEMINI_API_KEY")


def web_search_available() -> bool:
    """Google Search grounding is a Gemini-only capability."""
    return provider_name() == "gemini" and provider_is_configured()


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).strip().rstrip("/")


def _ollama_model(vision: bool = False) -> str:
    key = "OLLAMA_VISION_MODEL" if vision else "OLLAMA_MODEL"
    default = DEFAULT_OLLAMA_VISION_MODEL if vision else DEFAULT_OLLAMA_MODEL
    return os.environ.get(key, default).strip() or default


def _ollama_context_size() -> int:
    raw = os.environ.get("OLLAMA_NUM_CTX", str(DEFAULT_CONTEXT_SIZE)).strip()
    try:
        value = int(raw)
    except ValueError as e:
        raise LLMError(f"OLLAMA_NUM_CTX must be an integer, not {raw!r}.") from e
    if value < 1024:
        raise LLMError("OLLAMA_NUM_CTX must be at least 1024.")
    return value


def _read_http_error(e: urllib.error.HTTPError) -> str:
    try:
        data = json.loads(e.read() or b"{}")
        return str(data.get("error") or data.get("message") or "").strip()
    except (ValueError, OSError, AttributeError):
        return ""


def _ollama_error(e: urllib.error.HTTPError, model: str) -> LLMError:
    detail = _read_http_error(e)
    suffix = f": {detail}" if detail else "."
    if e.code == 404:
        return LLMError(f"Ollama model '{model}' is not installed. Run: ollama pull {model}")
    return LLMError(f"Ollama request failed with HTTP {e.code}{suffix}")


def _ollama_request(path: str, body: Optional[Dict[str, Any]] = None,
                    timeout: int = TIMEOUT_SECONDS) -> Dict[str, Any]:
    url = f"{_ollama_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        raise LLMError(
            f"Could not reach Ollama at {_ollama_base_url()} ({reason}). Start it with 'ollama serve'."
        ) from e
    except (TimeoutError, socket.timeout) as e:
        raise LLMError(f"Ollama did not answer within {timeout} seconds.") from e
    except json.JSONDecodeError as e:
        raise LLMError("Ollama returned an unreadable response.") from e


def _ask_ollama(prompt: str, want_json: bool = False,
                 image_bytes: Optional[bytes] = None,
                 timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> str:
    model = _ollama_model(vision=image_bytes is not None)
    message: Dict[str, Any] = {"role": "user", "content": prompt}
    if image_bytes is not None:
        message["images"] = [base64.b64encode(image_bytes).decode("ascii")]

    body: Dict[str, Any] = {
        "model": model,
        "messages": [message],
        "stream": False,
        "think": False,
        "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "5m"),
        "options": {
            "num_ctx": _ollama_context_size(),
            "temperature": 0 if want_json or fast else 0.2,
        },
    }
    if want_json:
        body["format"] = "json"
    try:
        data = _ollama_request("/api/chat", body, timeout)
    except urllib.error.HTTPError as e:
        raise _ollama_error(e, model) from e
    text = str((data.get("message") or {}).get("content") or "").strip()
    if not text:
        raise LLMError(f"Ollama model '{model}' returned an empty answer.")
    return text


def generate_text(prompt: str, want_json: bool = False, use_web_search: bool = False,
                  image_bytes: Optional[bytes] = None, image_mime: str = "image/png",
                  timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> Tuple[str, List[Dict[str, str]]]:
    """Generate text and return ``(answer, grounded_web_sources)`` for either provider."""
    provider = provider_name()
    if provider == "ollama":
        if use_web_search:
            raise LLMError(
                "Web research is unavailable with the local Ollama provider. "
                "Use uploaded files/local RAG, or set AI_PROVIDER=gemini for Google Search."
            )
        return _ask_ollama(prompt, want_json, image_bytes, timeout, fast), []

    from core.gemini_client import GeminiError, ask_gemini
    try:
        return ask_gemini(
            prompt,
            want_json=want_json,
            use_web_search=use_web_search,
            image_bytes=image_bytes,
            image_mime=image_mime,
            timeout=timeout,
            fast=fast,
        )
    except GeminiError as e:
        raise LLMError(str(e)) from e


def parse_json_answer(text: str) -> Dict[str, Any]:
    """Parse an object while tolerating markdown fences or surrounding prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        answer = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        answer = json.loads(cleaned[start:end + 1])
    if not isinstance(answer, dict):
        raise json.JSONDecodeError("expected a JSON object", cleaned, 0)
    return answer


def generate_json(prompt: str, timeout: int = TIMEOUT_SECONDS, fast: bool = False) -> Dict[str, Any]:
    """Generate a structured JSON object, retrying one malformed response."""
    last_error: Optional[json.JSONDecodeError] = None
    for attempt in range(JSON_ATTEMPTS):
        text, _ = generate_text(prompt, want_json=True, timeout=timeout, fast=fast)
        try:
            return parse_json_answer(text)
        except json.JSONDecodeError as e:
            last_error = e
            print(
                f"[{provider_name()}] attempt {attempt + 1}: invalid JSON "
                f"({e.msg} at {e.pos}/{len(text)} chars)",
                file=sys.stderr,
            )
    raise LLMError(
        f"{provider_label()} did not return valid JSON twice in a row. Please try again."
    ) from last_error


def get_provider_status(timeout: int = 5) -> Dict[str, Any]:
    """Return a JSON-serialisable health/configuration snapshot without generating tokens."""
    provider = provider_name()
    if provider == "gemini":
        from core.gemini_client import check_api_key
        status = check_api_key(timeout)
        return {
            "provider": provider,
            "label": "Gemini",
            "status": status,
            "ready": status == "ok",
            "model": os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
            "vision_model": os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
            "web_search": status == "ok",
        }

    model = _ollama_model()
    vision_model = _ollama_model(vision=True)
    try:
        data = _ollama_request("/api/tags", timeout=timeout)
    except urllib.error.HTTPError:
        status, installed = "unreachable", []
    except LLMError:
        status, installed = "unreachable", []
    else:
        installed = sorted({str(item.get("name") or item.get("model") or "")
                            for item in data.get("models", []) if isinstance(item, dict)})
        missing = [name for name in (model, vision_model) if name not in installed]
        status = "model_missing" if missing else "ok"
    return {
        "provider": provider,
        "label": "Ollama (local)",
        "status": status,
        "ready": status == "ok",
        "base_url": _ollama_base_url(),
        "model": model,
        "vision_model": vision_model,
        "installed_models": installed,
        "web_search": False,
    }
