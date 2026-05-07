"""File upload and processing services"""
import os
import whisper
from typing import List, Dict, Optional
from PyPDF2 import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def transcribe_audio_with_timestamps(file_path: str) -> Dict:
    """
    Transcribe audio/video file using Whisper with word-level timestamps.
    
    Returns:
        dict with keys:
        - text: full transcription
        - duration: total duration in seconds
        - segments: list of {text, start, end} dicts
    """
    try:
        # Load small model for speed; use "base" or "small" for better accuracy
        model = whisper.load_model("tiny")
        
        # Transcribe with word-level timestamps
        result = model.transcribe(
            file_path,
            word_timestamps=True,
            task="transcribe",
            language=None  # Auto-detect
        )
        
        # Extract segments with timestamps
        segments = []
        for segment in result.get("segments", []):
            segments.append({
                "text": segment.get("text", "").strip(),
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "words": segment.get("words", [])  # Word-level timestamps if needed
            })
        
        return {
            "text": result.get("text", "").strip(),
            "duration": result.get("duration", 0),
            "segments": segments
        }
    except Exception as e:
        raise RuntimeError(f"Whisper transcription failed: {e}")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundary
        if end < len(text):
            # Look for period, exclamation, or question mark
            for punct in [".", "!", "?", "\n"]:
                pos = text.rfind(punct, start, end)
                if pos > start + chunk_size // 2:
                    end = pos + 1
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap
    return chunks


def chunk_text_with_timestamps(
    full_text: str,
    segments: List[Dict],
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Dict]:
    """
    Split transcribed text into chunks while preserving timestamp metadata.
    
    Returns list of dicts: {text, start_time, end_time, segment_indices}
    """
    if not segments:
        # Fallback to plain chunking if no segments
        return [{"text": t, "start_time": None, "end_time": None} for t in chunk_text(full_text, chunk_size, overlap)]
    
    chunks = []
    current_text = ""
    current_start = None
    current_end = None
    segment_indices = []
    
    for i, seg in enumerate(segments):
        seg_text = seg.get("text", "").strip()
        seg_start = seg.get("start")
        seg_end = seg.get("end")
        
        if not seg_text:
            continue
            
        # Add segment to current chunk
        if current_text:
            current_text += " " + seg_text
        else:
            current_text = seg_text
            current_start = seg_start
        
        current_end = seg_end
        segment_indices.append(i)
        
        # If chunk is big enough, save it
        if len(current_text) >= chunk_size:
            chunks.append({
                "text": current_text.strip(),
                "start_time": current_start,
                "end_time": current_end,
                "segment_indices": segment_indices.copy()
            })
            # Start new chunk with overlap from last few segments
            overlap_text = " ".join(segments[j]["text"] for j in segment_indices[-3:] if j < len(segments))
            current_text = overlap_text.strip() if overlap_text else seg_text
            current_start = segments[segment_indices[-3]]["start"] if len(segment_indices) >= 3 else seg_start
            segment_indices = segment_indices[-3:]
    
    # Don't forget the last chunk
    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "start_time": current_start,
            "end_time": current_end,
            "segment_indices": segment_indices
        })
    
    return chunks