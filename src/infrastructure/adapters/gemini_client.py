# Cliente Gemini usando API v1 e modelos 2.x
import os
from typing import Optional
from google import genai
from google.genai import types
from google.genai.types import HttpOptions  # << importa HttpOptions
from src.application.logging_setup import app_logger

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # << nome novo recomendado

def _build_client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("Env GOOGLE_API_KEY ausente.")
    # força API v1 (evita 404 de v1beta)
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version="v1"))

def generate_completion_gemini(prompt: str,
                               model: Optional[str] = None,
                               temperature: float = 0.2) -> str:
    client = _build_client()
    model = model or DEFAULT_MODEL

    safety = [
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_MEDIUM_AND_ABOVE"),
    ]

    try:
        resp = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(temperature=temperature,
                                               safety_settings=safety),
        )
        text = getattr(resp, "text", "") or ""
        if not text and getattr(resp, "candidates", None):
            text = "".join(
                p.text
                for c in resp.candidates
                for p in getattr(c, "content", types.Content()).parts or []
                if hasattr(p, "text") and p.text
            )
        return (text or "").strip() or "[Gemini não retornou texto]"
    except Exception as e:
        app_logger.info({"event": "gemini_error", "error": repr(e), "model": model})
        raise

