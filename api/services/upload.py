"""Services for file upload processing: PDF, audio, video"""
#api\services\upload.py
import os
import whisper
from typing import List, Dict, Optional
import PyPDF2
from django.conf import settings


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file using PyPDF2"""
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def transcribe_audio_with_timestamps(file_path: str, model_size: str = "base") -> Dict[str, any]:
    """
    Transcribe audio/video using Whisper and return text + timestamps.
    
    Returns:
        dict: {
            'text': str,  # Full transcription
            'segments': List[Dict],  # [{start, end, text}, ...]
            'duration': float  # Total duration in seconds
        }
    """
    # Load Whisper model (cached after first load)
    model = whisper.load_model(model_size)
    
    # Transcribe with word-level timestamps
    result = model.transcribe(
        file_path,
        task="transcribe",
        language=None,  # Auto-detect
        verbose=False,
        word_timestamps=True  # Critical for timestamp extraction
    )
    
    # Extract segments with timestamps
    segments = []
    for segment in result.get('segments', []):
        segments.append({
            'start': round(segment['start'], 2),
            'end': round(segment['end'], 2),
            'text': segment['text'].strip()
        })
    
    return {
        'text': result['text'].strip(),
        'segments': segments,
        'duration': result.get('duration', 0)
    }


def chunk_text_with_timestamps(
    text: str, 
    segments: List[Dict], 
    chunk_size: int = 1000, 
    overlap: int = 200
) -> List[Dict]:
    """
    Split text into chunks while preserving timestamp metadata.
    
    Args:
        text: Full transcribed text
        segments: List of {start, end, text} from Whisper
        chunk_size: Target characters per chunk
        overlap: Overlap between chunks in characters
    
    Returns:
        List of chunks with metadata: [{text, start_time, end_time, segment_indices}, ...]
    """
    if not segments:
        # Fallback: simple text chunking without timestamps
        chunks = chunk_text(text, chunk_size, overlap)
        return [{'text': c, 'start_time': 0, 'end_time': None, 'segment_indices': []} for c in chunks]
    
    chunks = []
    current_chunk = []
    current_length = 0
    start_idx = 0
    
    for i, seg in enumerate(segments):
        seg_text = seg['text']
        seg_len = len(seg_text)
        
        # Add segment to current chunk if it fits
        if current_length + seg_len <= chunk_size or not current_chunk:
            current_chunk.append(seg)
            current_length += seg_len
        else:
            # Save current chunk and start new one
            if current_chunk:
                chunks.append({
                    'text': ' '.join(s['text'] for s in current_chunk),
                    'start_time': current_chunk[0]['start'],
                    'end_time': current_chunk[-1]['end'],
                    'segment_indices': list(range(start_idx, i))
                })
            # Start new chunk with overlap
            overlap_segs = current_chunk[-(overlap//100 + 1):] if overlap > 0 else []
            current_chunk = overlap_segs + [seg]
            current_length = sum(len(s['text']) for s in current_chunk)
            start_idx = i - len(overlap_segs)
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append({
            'text': ' '.join(s['text'] for s in current_chunk),
            'start_time': current_chunk[0]['start'],
            'end_time': current_chunk[-1]['end'],
            'segment_indices': list(range(start_idx, len(segments)))
        })
    
    return chunks


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple text chunking without timestamps (fallback)"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks if chunks else [text]