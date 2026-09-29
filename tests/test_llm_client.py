"""Provider-neutral LLM client tests. All HTTP calls are mocked."""
import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from core.llm_client import (
    LLMError,
    generate_json,
    generate_text,
    get_provider_status,
    provider_name,
)


def response(body: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(body).encode())


@mock.patch.dict(os.environ, {
    "AI_PROVIDER": "ollama",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "qwen3:14b",
    "OLLAMA_VISION_MODEL": "qwen3-vl:8b",
    "OLLAMA_NUM_CTX": "8192",
})
class OllamaClientTests(unittest.TestCase):
    def test_text_request_uses_local_chat_api_and_configured_model(self):
        with mock.patch("urllib.request.urlopen", return_value=response({"message": {"content": "hello"}})) as open_url:
            text, sources = generate_text("Hi")

        self.assertEqual((text, sources), ("hello", []))
        request = open_url.call_args.args[0]
        sent = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(sent["model"], "qwen3:14b")
        self.assertEqual(sent["options"]["num_ctx"], 8192)
        self.assertFalse(sent["stream"])

    def test_json_request_enables_structured_output(self):
        with mock.patch("urllib.request.urlopen", return_value=response({"message": {"content": '{"answer": 7}'}})) as open_url:
            self.assertEqual(generate_json("Return an object"), {"answer": 7})

        sent = json.loads(open_url.call_args.args[0].data)
        self.assertEqual(sent["format"], "json")
        self.assertEqual(sent["options"]["temperature"], 0)

    def test_json_retries_one_malformed_answer(self):
        replies = [response({"message": {"content": "{"}}),
                   response({"message": {"content": '{"ok": true}'}})]
        with mock.patch("urllib.request.urlopen", side_effect=replies) as open_url:
            self.assertEqual(generate_json("Return JSON"), {"ok": True})
        self.assertEqual(open_url.call_count, 2)

    def test_image_uses_vision_model_and_base64(self):
        with mock.patch("urllib.request.urlopen", return_value=response({"message": {"content": "invoice"}})) as open_url:
            text, _ = generate_text("Read", image_bytes=b"image-bytes", image_mime="image/png")

        sent = json.loads(open_url.call_args.args[0].data)
        self.assertEqual(text, "invoice")
        self.assertEqual(sent["model"], "qwen3-vl:8b")
        self.assertEqual(sent["messages"][0]["images"], ["aW1hZ2UtYnl0ZXM="])

    def test_status_reports_missing_and_installed_models(self):
        tags = {"models": [{"name": "qwen3:14b"}]}
        with mock.patch("urllib.request.urlopen", return_value=response(tags)):
            status = get_provider_status()
        self.assertEqual(status["status"], "model_missing")
        self.assertFalse(status["ready"])

        tags["models"].append({"name": "qwen3-vl:8b"})
        with mock.patch("urllib.request.urlopen", return_value=response(tags)):
            status = get_provider_status()
        self.assertEqual(status["status"], "ok")
        self.assertTrue(status["ready"])

    def test_missing_model_error_says_how_to_install(self):
        error = urllib.error.HTTPError(
            "http://127.0.0.1:11434/api/chat", 404, "Not Found", {},
            io.BytesIO(b'{"error":"model not found"}'),
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(LLMError, r"ollama pull qwen3:14b"):
                generate_text("Hi")

    def test_web_search_is_explicitly_gemini_only(self):
        with self.assertRaisesRegex(LLMError, "AI_PROVIDER=gemini"):
            generate_text("news", use_web_search=True)


class ProviderSelectionTests(unittest.TestCase):
    def test_unknown_provider_is_rejected(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER": "unknown"}):
            with self.assertRaisesRegex(LLMError, "Unsupported AI_PROVIDER"):
                provider_name()

    def test_gemini_dispatch_is_preserved(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "key"}), \
                mock.patch("core.gemini_client.ask_gemini", return_value=("cloud", [])) as ask:
            self.assertEqual(generate_text("hello"), ("cloud", []))
        ask.assert_called_once()


if __name__ == "__main__":
    unittest.main()
