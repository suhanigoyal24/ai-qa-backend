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
    from disk rather than downloading it during the first user upload.
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
            word_timestamps=True,
            task="transcribe",
            language=None,
            fp16=False,
            verbose=False,
        )

        segments = []

        for segment in result.get("segments", []):
            segments.append(
                {
                    "text": segment.get("text", "").strip(),
                    "start": float(segment.get("start", 0)),
                    "end": float(segment.get("end", 0)),
                    "words": segment.get("words", []),
                }
            )

        duration = 0.0
        if segments:
            duration = float(segments[-1].get("end", 0))

        transcript = result.get("text", "").strip()
        detected_language = result.get("language")

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
    """Split text into overlapping chunks for embedding."""
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
    Split a transcription into chunks while preserving timestamp metadata.

    Returns:
        A list of dictionaries containing:
        - text
        - start_time
        - end_time
        - segment_indices
    """
    if not segments:
        return [
            {
                "text": chunk,
                "start_time": None,
                "end_time": None,
                "segment_indices": [],
            }
            for chunk in chunk_text(
                full_text,
                chunk_size,
                overlap,
            )
        ]

    chunks: List[Dict] = []
    current_text_parts: List[str] = []
    current_start = None
    current_end = None
    current_segment_indices: List[int] = []

    for index, segment in enumerate(segments):
        segment_text = segment.get("text", "").strip()

        if not segment_text:
            continue

        segment_start = segment.get("start")
        segment_end = segment.get("end")

        if current_start is None:
            current_start = segment_start

        current_text_parts.append(segment_text)
        current_end = segment_end
        current_segment_indices.append(index)

        current_text = " ".join(current_text_parts).strip()

        if len(current_text) >= chunk_size:
            chunks.append(
                {
                    "text": current_text,
                    "start_time": current_start,
                    "end_time": current_end,
                    "segment_indices": (
                        current_segment_indices.copy()
                    ),
                }
            )

            overlap_indices = current_segment_indices[-3:]

            current_text_parts = [
                segments[segment_index].get("text", "").strip()
                for segment_index in overlap_indices
                if segments[segment_index].get("text", "").strip()
            ]

            current_segment_indices = overlap_indices.copy()

            if overlap_indices:
                current_start = segments[
                    overlap_indices[0]
                ].get("start")
            else:
                current_start = None

    remaining_text = " ".join(current_text_parts).strip()

    if remaining_text:
        last_chunk = {
            "text": remaining_text,
            "start_time": current_start,
            "end_time": current_end,
            "segment_indices": current_segment_indices.copy(),
        }

        if not chunks or last_chunk["text"] != chunks[-1]["text"]:
            chunks.append(last_chunk)

    return chunks