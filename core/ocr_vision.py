"""Image text extraction (OCR) using the configured provider's vision model."""
from core.llm_client import generate_text

MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def read_image_text(path: str) -> str:
    extension = path[path.rfind("."):].lower()
    with open(path, "rb") as f:
        image_bytes = f.read()
    text, _ = generate_text(
        "Transcribe all readable text in this image. If it is a diagram, also describe it in a few sentences.",
        image_bytes=image_bytes,
        image_mime=MIME_TYPES.get(extension, "image/png"),
    )
    return text
