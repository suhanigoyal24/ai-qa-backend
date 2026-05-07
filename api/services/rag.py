"""RAG (Retrieval-Augmented Generation) services using FAISS"""
import os
import faiss
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


# Global cache for embeddings instance
_embeddings = None


def get_embeddings():
    """Lazy-load Gemini embeddings with CORRECT model name"""
    global _embeddings
    if _embeddings is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # CORRECT MODEL: text-embedding-004 (NOT embedding-001)
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=api_key,
            task_type="RETRIEVAL_DOCUMENT"
        )
    return _embeddings


def create_faiss_index(chunks: List[Dict], file_id: str) -> str:
    """
    Create FAISS index from text chunks and save to disk.
    
    Args:
        chunks: List of dicts with 'text' key
        file_id: Unique identifier for the file
    
    Returns:
        str: Path to the saved .faiss index file
    """
    # Extract texts for embedding
    texts = [chunk['text'] if isinstance(chunk, dict) else chunk for chunk in chunks]
    
    # Generate embeddings using correct model
    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(texts)
    
    # Create FAISS index (cosine similarity via L2 on normalized vectors)
    dimension = len(vectors[0])
    index = faiss.IndexFlatL2(dimension)
    
    # Normalize vectors for cosine similarity
    vectors_array = np.array(vectors).astype('float32')
    faiss.normalize_L2(vectors_array)
    index.add(vectors_array)
    
    # Save index and metadata
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    faiss_dir.mkdir(exist_ok=True)
    
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    faiss.write_index(index, str(index_path))
    
    # Save chunk metadata (including timestamps if present)
    metadata = []
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            metadata.append({
                'index': i,
                'text': chunk.get('text', ''),
                'start_time': chunk.get('start_time'),
                'end_time': chunk.get('end_time'),
                'segment_indices': chunk.get('segment_indices', [])
            })
        else:
            metadata.append({'index': i, 'text': str(chunk)})
    
    with open(metadata_path, 'wb') as f:
        pickle.dump({'chunks': metadata, 'count': len(metadata)}, f)
    
    return str(index_path)


def search_similar(query: str, file_id: str, top_k: int = 3) -> List[Dict]:
    """
    Search for similar chunks using FAISS.
    
    Returns:
        List of results with text, timestamp metadata, and similarity score
    """
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    if not index_path.exists() or not metadata_path.exists():
        return []
    
    # Load index
    index = faiss.read_index(str(index_path))
    
    # Load metadata
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    
    # Embed and normalize query using correct model
    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    query_array = np.array([query_vector]).astype('float32')
    faiss.normalize_L2(query_array)
    
    # Search
    D, I = index.search(query_array, min(top_k, metadata['count']))
    
    # Build results with timestamp info
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(metadata['chunks']):
            chunk_meta = metadata['chunks'][idx]
            results.append({
                'chunk_index': chunk_meta.get('index', idx),
                'text': chunk_meta.get('text', ''),
                'start_time': chunk_meta.get('start_time'),
                'end_time': chunk_meta.get('end_time'),
                'segment_indices': chunk_meta.get('segment_indices', []),
                'score': float(dist)  # Lower = more similar (L2 distance)
            })
    
    return results


def get_context_from_results(results: List[Dict]) -> str:
    """Combine search results into context string for LLM"""
    if not results:
        return ""
    
    context_parts = []
    for i, result in enumerate(results, 1):
        time_info = ""
        if result.get('start_time') is not None:
            time_info = f" [Timestamp: {result['start_time']:.1f}s-{result['end_time']:.1f}s]"
        context_parts.append(f"[Chunk {result['chunk_index']}{time_info}]: {result['text']}")
    
    return "\n\n".join(context_parts)


def extract_best_timestamp(results: List[Dict]) -> Optional[float]:
    """
    Extract the most relevant timestamp from search results for playback.
    Returns the start_time of the highest-ranked result with timestamp info.
    """
    for result in results:
        if result.get('start_time') is not None:
            return result['start_time']
    return None