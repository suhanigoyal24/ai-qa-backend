"""File upload and processing services."""

import logging
import os
from functools import lru_cache
from typing import Dict, List

import whisper
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "tiny")
WHISPER_CACHE_DIR = os.getenv(
    "WHISPER_CACHE_DIR",
    os.path.join(os.path.expanduser("~"), ".cache", "whisper"),
)


@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Load and cache one Whisper model instance per Python process.

    The Docker image downloads the model during build, so this should load it
    from disk instead of downloading it during the first user upload.
    """
    logger.info(
        "Loading Whisper model '%s' from '%s'",
        WHISPER_MODEL_NAME,
        WHISPER_CACHE_DIR,
    )

    model = whisper.load_model(
        WHISPER_MODEL_NAME,
        download_root=WHISPER_CACHE_DIR,
        device="cpu",
    )

    logger.info("Whisper model loaded successfully")
    return model


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(file_path)
        extracted_pages: List[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text)

        return "\n".join(extracted_pages).strip()

    except Exception as exc:
        logger.exception("PDF extraction failed for %s", file_path)
        raise RuntimeError(
            f"Failed to extract text from PDF: {exc}"
        ) from exc


def transcribe_audio_with_timestamps(file_path: str) -> Dict:
    """
    Transcribe an audio or video file using Whisper.

    Whisper segment timestamps are retained. Word-level alignment is disabled
    because this application stores and retrieves segment start/end times.

    Returns:
        A dictionary containing:
        - text: complete transcription
        - duration: approximate duration in seconds
        - segments: timestamped transcription segments
        - language: detected language
    """
    try:
        model = get_whisper_model()

        logger.info("Starting Whisper transcription for %s", file_path)

        result = model.transcribe(
            file_path,
            word_timestamps=False,
            condition_on_previous_text=False,
            task="transcribe",
            language=None,
            temperature=0.0,
            fp16=False,
            verbose=False,
        )

        segments: List[Dict] = []

        for segment in result.get("segments", []):
            segment_text = segment.get("text", "").strip()

            if not segment_text:
                continue

            segments.append(
                {
                    "text": segment_text,
                    "start": float(segment.get("start", 0)),
                    "end": float(segment.get("end", 0)),
                }
            )

        transcript = result.get("text", "").strip()
        detected_language = result.get("language")

        if not transcript or not segments:
            raise RuntimeError(
                "No clear speech was detected in the uploaded audio or video."
            )

        duration = float(segments[-1].get("end", 0))

        logger.info(
            "Whisper completed transcription: language=%s, "
            "characters=%s, segments=%s, duration=%.2f",
            detected_language,
            len(transcript),
            len(segments),
            duration,
        )

        return {
            "text": transcript,
            "duration": duration,
            "segments": segments,
            "language": detected_language,
        }

    except Exception as exc:
        logger.exception("Whisper transcription failed for %s", file_path)
        raise RuntimeError(
            f"Whisper transcription failed: {exc}"
        ) from exc


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            for punctuation in [".", "!", "?", "\n"]:
                position = text.rfind(
                    punctuation,
                    start,
                    end,
                )

                if position > start + (chunk_size // 2):
                    end = position + 1
                    break

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(end - overlap, start + 1)

    return chunks


def chunk_text_with_timestamps(
    full_text: str,
    segments: List[Dict],
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[Dict]:
    """
    Create one searchable chunk per Whisper segment.

    A retrieved line therefore points to the start/end time of the segment in
    which it was spoken instead of the beginning of a large 1000-character
    block containing several unrelated lines.
    """
    chunks: List[Dict] = []

    for index, segment in enumerate(segments):
        segment_text = segment.get("text", "").strip()

        if not segment_text:
            continue

        start = segment.get("start")
        end = segment.get("end")

        chunks.append(
            {
                "text": segment_text,
                "start_time": float(start) if start is not None else None,
                "end_time": float(end) if end is not None else None,
                "segment_indices": [index],
            }
        )

    if chunks:
        return chunks

    # Defensive fallback for text sources that contain no timestamp segments.
    return [
        {
            "text": chunk,
            "start_time": None,
            "end_time": None,
            "segment_indices": [],
        }
        for chunk in chunk_text(full_text, chunk_size, overlap)
    ]