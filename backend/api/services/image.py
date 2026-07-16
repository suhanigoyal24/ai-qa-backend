"""Image understanding services using Gemini vision."""

import json
import logging
import os
from typing import Dict, List

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_IMAGE_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-3.1-flash-lite",
)


def _parse_json_response(response_text: str) -> Dict:
    """Parse a JSON response with a defensive code-fence fallback."""
    text = (response_text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError(
                "The image model returned an invalid analysis response."
            )
        data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise RuntimeError(
            "The image model returned an unexpected analysis response."
        )

    return data


def analyze_image(file_path: str) -> str:
    """Describe an image and extract visible text for downstream RAG."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is required for image analysis."
        )

    prompt = """Analyze this image carefully and return JSON only:
{
  "summary": "A concise factual overview",
  "visual_description": "Objects, people, actions, setting, and layout",
  "visible_text": "All clearly readable text, or an empty string",
  "notable_details": ["Important factual detail"]
}

Do not identify unknown people or invent unreadable text. Do not use Markdown.
"""

    uploaded_file = None

    try:
        with genai.Client(api_key=api_key) as client:
            uploaded_file = client.files.upload(file=file_path)
            response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            data = _parse_json_response(response.text)

        summary = str(data.get("summary", "")).strip()
        description = str(
            data.get("visual_description", "")
        ).strip()
        visible_text = str(data.get("visible_text", "")).strip()
        raw_details = data.get("notable_details", [])
        details: List[str] = []

        if isinstance(raw_details, list):
            details = [
                str(detail).strip()
                for detail in raw_details
                if str(detail).strip()
            ]

        parts = []
        if summary:
            parts.append(f"Image overview: {summary}")
        if description:
            parts.append(f"Visual description: {description}")
        if visible_text:
            parts.append(f"Visible text: {visible_text}")
        if details:
            parts.append(f"Notable details: {'; '.join(details)}")

        result = "\n".join(parts).strip()
        if not result:
            raise RuntimeError(
                "No usable visual information was returned for the image."
            )

        logger.info("Image analysis completed for %s", file_path)
        return result
    except Exception as exc:
        logger.exception("Image analysis failed for %s", file_path)
        raise RuntimeError(f"Image analysis failed: {exc}") from exc
    finally:
        if uploaded_file is not None:
            try:
                with genai.Client(api_key=api_key) as cleanup_client:
                    cleanup_client.files.delete(name=uploaded_file.name)
            except Exception:
                logger.warning(
                    "Could not delete temporary Gemini image file %s",
                    getattr(uploaded_file, "name", "unknown"),
                    exc_info=True,
                )
