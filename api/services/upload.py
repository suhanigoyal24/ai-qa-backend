import os
import PyPDF2
import whisper
from django.conf import settings

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def transcribe_audio(file_path: str) -> str:
    """Transcribe audio/video using Whisper"""
    # Use base model (faster, good accuracy). Use 'medium' or 'large' for better quality
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks if chunks else [text]  # Fallback if chunking fails