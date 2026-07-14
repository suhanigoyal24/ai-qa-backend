"""Visual and audible video analysis using the Gemini Files API."""

import json
import logging
import os
import subprocess
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_VIDEO_MODEL = os.getenv(
    "GEMINI_VIDEO_MODEL",
    "gemini-2.5-flash",
)
VIDEO_PROCESSING_TIMEOUT = int(
    os.getenv("VIDEO_PROCESSING_TIMEOUT", "600")
)


def _to_float(value, default: float = 0.0) -> float:
    """Convert a model-provided value to a non-negative float."""
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return default


def _get_video_duration(file_path: str) -> Optional[float]:
    """Read the container duration using ffprobe when available."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = float(result.stdout.strip())
        return duration if duration > 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        logger.warning("Could not determine video duration for %s", file_path)
        return None


def _parse_json_response(response_text: str) -> Dict:
    """Parse JSON even if the provider surrounds it with a code fence."""
    text = (response_text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
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
                "The video model returned an invalid analysis response."
            )
        data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise RuntimeError(
            "The video model returned an unexpected analysis response."
        )

    return data


def _wait_until_ready(client, uploaded_file):
    """Wait for Gemini to finish preparing an uploaded video."""
    deadline = time.monotonic() + VIDEO_PROCESSING_TIMEOUT
    current_file = uploaded_file

    while True:
        state = getattr(current_file, "state", None)
        state_name = str(getattr(state, "name", state) or "").upper()

        if state_name not in {"PROCESSING", "FILE_STATE_PROCESSING"}:
            if state_name in {"FAILED", "FILE_STATE_FAILED"}:
                raise RuntimeError(
                    "Gemini could not process the uploaded video."
                )
            return current_file

        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Timed out while waiting for Gemini to process the video."
            )

        time.sleep(2)
        current_file = client.files.get(name=current_file.name)


def _normalise_scenes(
    raw_scenes: List[Dict],
    duration: Optional[float],
) -> List[Dict]:
    """Validate model output and convert it into timestamped RAG segments."""
    scenes: List[Dict] = []

    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict):
            continue

        visual = str(raw_scene.get("visual_description", "")).strip()
        spoken = str(raw_scene.get("spoken_text", "")).strip()

        if spoken.lower() in {
            "none",
            "null",
            "n/a",
            "no speech",
            "no audible speech",
        }:
            spoken = ""

        if not visual and not spoken:
            continue

        start = _to_float(raw_scene.get("start_time"), 0.0)
        end = _to_float(raw_scene.get("end_time"), start)

        if duration is not None:
            start = min(start, duration)
            end = min(end, duration)

        end = max(end, start)

        text_parts = []
        if visual:
            text_parts.append(f"Visual: {visual}")
        if spoken:
            text_parts.append(f"Spoken audio: {spoken}")

        scenes.append(
            {
                "text": " ".join(text_parts),
                "start": start,
                "end": end,
            }
        )

    scenes.sort(key=lambda scene: (scene["start"], scene["end"]))
    return scenes


def analyze_video_with_timestamps(file_path: str) -> Dict:
    """
    Analyze visible video content and clearly audible speech with timestamps.

    The result uses the same text/duration/segments shape as the audio
    transcription service, so the existing RAG pipeline can index it.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is required for visual video analysis."
        )

    duration = _get_video_duration(file_path)
    duration_instruction = (
        f"The video duration is approximately {duration:.2f} seconds."
        if duration is not None
        else "Determine the video duration from the uploaded media."
    )

    prompt = f"""Analyze this video's frames and audio track.

{duration_instruction}

Return one JSON object with exactly this structure:
{{
  "summary": "A concise factual overview of the video",
  "has_audible_speech": false,
  "scenes": [
    {{
      "start_time": 0.0,
      "end_time": 5.0,
      "visual_description": "What is visibly present and happening",
      "spoken_text": "Exact clearly audible speech, or an empty string"
    }}
  ]
}}

Rules:
- Base visual descriptions only on visible frames.
- Cover the full timeline with useful scene boundaries and timestamps.
- Describe objects, people, movement, setting, and important changes.
- Do not infer identities, intentions, dialogue, or sounds that are unclear.
- If there is no clearly intelligible speech, use an empty spoken_text and set
  has_audible_speech to false.
- Never invent words for silent footage, music, engine noise, or background
  noise.
- Use seconds as numbers and return JSON only, with no Markdown.
"""

    uploaded_file = None

    try:
        with genai.Client(api_key=api_key) as client:
            logger.info(
                "Uploading video for visual analysis with model %s",
                GEMINI_VIDEO_MODEL,
            )
            uploaded_file = client.files.upload(file=file_path)
            uploaded_file = _wait_until_ready(client, uploaded_file)

            response = client.models.generate_content(
                model=GEMINI_VIDEO_MODEL,
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            data = _parse_json_response(response.text)
            raw_scenes = data.get("scenes", [])
            if not isinstance(raw_scenes, list):
                raw_scenes = []

            scenes = _normalise_scenes(raw_scenes, duration)
            summary = str(data.get("summary", "")).strip()

            if not summary and scenes:
                summary = " ".join(
                    scene["text"] for scene in scenes[:5]
                )

            if not summary and not scenes:
                raise RuntimeError(
                    "No usable visual information was returned for the video."
                )

            if duration is None:
                duration = max(
                    (scene["end"] for scene in scenes),
                    default=0.0,
                )

            segments = []
            if summary:
                segments.append(
                    {
                        "text": f"Visual overview: {summary}",
                        "start": 0.0,
                        "end": duration or 0.0,
                    }
                )
            segments.extend(scenes)

            text = " ".join(
                segment["text"] for segment in segments
            ).strip()

            logger.info(
                "Video analysis completed: scenes=%s duration=%.2f "
                "audible_speech=%s",
                len(scenes),
                duration or 0.0,
                bool(data.get("has_audible_speech", False)),
            )

            return {
                "text": text,
                "duration": float(duration or 0.0),
                "segments": segments,
                "summary": summary,
                "has_audible_speech": bool(
                    data.get("has_audible_speech", False)
                ),
            }
    except Exception as exc:
        logger.exception("Visual video analysis failed for %s", file_path)
        raise RuntimeError(
            f"Visual video analysis failed: {exc}"
        ) from exc
    finally:
        if uploaded_file is not None:
            try:
                with genai.Client(api_key=api_key) as cleanup_client:
                    cleanup_client.files.delete(name=uploaded_file.name)
            except Exception:
                logger.warning(
                    "Could not delete temporary Gemini video file %s",
                    getattr(uploaded_file, "name", "unknown"),
                    exc_info=True,
                )
