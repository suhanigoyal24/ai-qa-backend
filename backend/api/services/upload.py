"""File upload and processing services."""

import logging
import os
from functools import lru_cache
from typing import Dict, List

import numpy as np
import whisper
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "tiny")
WHISPER_CACHE_DIR = os.getenv(
    "WHISPER_CACHE_DIR",
    os.path.join(os.path.expanduser("~"), ".cache", "whisper"),
)
WHISPER_SAMPLE_RATE = 16000
MIN_AUDIO_RMS = float(os.getenv("MIN_AUDIO_RMS", "0.0005"))


class NoUsableSpeechError(RuntimeError):
    """Raised when an audio file has no readable stream or clear speech."""


def _audio_rms(audio: np.ndarray) -> float:
    """Return the root-mean-square amplitude of normalized audio samples."""
    if audio.size == 0:
        return 0.0

    samples = np.asarray(audio, dtype=np.float64)
    return float(np.sqrt(np.mean(np.square(samples))))


def _load_audio(file_path: str) -> np.ndarray:
    """Decode audio and reject files with no usable audio signal."""
    try:
        audio = whisper.load_audio(file_path)
    except Exception as exc:
        raise NoUsableSpeechError(
            "No readable audio stream was found in the uploaded file."
        ) from exc

    if audio.size == 0 or _audio_rms(audio) < MIN_AUDIO_RMS:
        raise NoUsableSpeechError(
            "No usable speech was detected in the uploaded audio."
        )

    return audio


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


def extract_text_file(file_path: str) -> str:
    """Read a plain-text, Markdown, CSV, or JSON file safely."""
    last_error = None

    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as text_file:
                text = text_file.read().strip()

            if not text:
                raise RuntimeError("The uploaded text file is empty.")

            return text
        except UnicodeError as exc:
            last_error = exc

    raise RuntimeError(
        f"Could not decode the uploaded text file: {last_error}"
    )


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
        audio = _load_audio(file_path)
        model = get_whisper_model()

        logger.info("Starting Whisper transcription for %s", file_path)

        result = model.transcribe(
            audio,
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

            start = max(float(segment.get("start", 0)), 0.0)
            end = max(float(segment.get("end", start)), start)
            start_sample = int(start * WHISPER_SAMPLE_RATE)
            end_sample = int(end * WHISPER_SAMPLE_RATE)
            segment_audio = audio[start_sample:end_sample]
            segment_rms = _audio_rms(segment_audio)
            no_speech_probability = float(
                segment.get("no_speech_prob", 0.0)
            )
            average_log_probability = float(
                segment.get("avg_logprob", 0.0)
            )

            # Whisper can generate plausible words over silence or noise.
            # Require both a real signal and reasonable model confidence.
            if segment_rms < MIN_AUDIO_RMS:
                continue

            if (
                no_speech_probability >= 0.80
                or average_log_probability < -1.20
            ):
                logger.info(
                    "Skipping low-confidence Whisper segment: "
                    "start=%.2f end=%.2f no_speech=%.3f avg_logprob=%.3f",
                    start,
                    end,
                    no_speech_probability,
                    average_log_probability,
                )
                continue

            segments.append(
                {
                    "text": segment_text,
                    "start": start,
                    "end": end,
                }
            )

        transcript = " ".join(
            segment["text"] for segment in segments
        ).strip()
        detected_language = result.get("language")

        if not transcript or not segments:
            raise NoUsableSpeechError(
                "No clear speech was detected in the uploaded audio or video."
            )

        duration = float(len(audio) / WHISPER_SAMPLE_RATE)

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

    except NoUsableSpeechError:
        logger.info("No usable speech found in %s", file_path)
        raise
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
