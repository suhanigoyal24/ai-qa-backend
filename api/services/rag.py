"""RAG (Retrieval-Augmented Generation) services using FAISS"""
import os
import faiss
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    HAS_GOOGLE_EMBEDDINGS = True
except ImportError:
    HAS_GOOGLE_EMBEDDINGS = False


_embeddings = None
_USE_MOCK = os.getenv("USE_MOCK_EMBEDDINGS", "False").lower() == "true"


def _mock_embed(texts: List[str]) -> List[List[float]]:
    """Mock embeddings for demo/testing."""
    import hashlib
    vectors = []
    for text in texts:
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = [(hash_bytes[i % len(hash_bytes)] / 255.0 - 0.5) * 2 for i in range(768)]
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        vectors.append(vector)
    return vectors


def get_embeddings():
    """Lazy-load embeddings with fallback to mock."""
    global _embeddings
    
    if _USE_MOCK:
        class MockEmbeddings:
            def embed_documents(self, texts): return _mock_embed(texts)
            def embed_query(self, text): return _mock_embed([text])[0]
        return MockEmbeddings()
    
    if _embeddings is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            class MockEmbeddings:
                def embed_documents(self, texts): return _mock_embed(texts)
                def embed_query(self, text): return _mock_embed([text])[0]
            _embeddings = MockEmbeddings()
            return _embeddings
        try:
            _embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=api_key,
                task_type="RETRIEVAL_DOCUMENT"
            )
            _embeddings.embed_query("test")
        except Exception:
            class MockEmbeddings:
                def embed_documents(self, texts): return _mock_embed(texts)
                def embed_query(self, text): return _mock_embed([text])[0]
            _embeddings = MockEmbeddings()
    return _embeddings


def create_faiss_index(chunks: List[Dict], file_id: str) -> str:
    """Create FAISS index from text chunks with timestamp metadata."""
    texts = [chunk['text'] if isinstance(chunk, dict) else chunk for chunk in chunks]
    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(texts)
    
    dimension = len(vectors[0])
    index = faiss.IndexFlatL2(dimension)
    vectors_array = np.array(vectors).astype('float32')
    faiss.normalize_L2(vectors_array)
    index.add(vectors_array)
    
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    faiss_dir.mkdir(exist_ok=True)
    
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    faiss.write_index(index, str(index_path))
    
    # Save metadata with timestamps
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
            metadata.append({'index': i, 'text': str(chunk), 'start_time': None, 'end_time': None})
    
    with open(metadata_path, 'wb') as f:
        pickle.dump({'chunks': metadata, 'count': len(metadata)}, f)
    
    return str(index_path)


def search_similar(query: str, file_id: str, top_k: int = 3) -> List[Dict]:
    """Search for similar chunks using FAISS, return with timestamp metadata."""
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    if not index_path.exists() or not metadata_path.exists():
        return []
    
    index = faiss.read_index(str(index_path))
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    
    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    query_array = np.array([query_vector]).astype('float32')
    faiss.normalize_L2(query_array)
    
    D, I = index.search(query_array, min(top_k, metadata['count']))
    
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(metadata['chunks']):
            chunk_meta = metadata['chunks'][idx]
            results.append({
                'chunk_index': chunk_meta.get('index', idx),
                'text': chunk_meta.get('text', ''),
                'start_time': chunk_meta.get('start_time'),  # Real timestamp
                'end_time': chunk_meta.get('end_time'),
                'segment_indices': chunk_meta.get('segment_indices', []),
                'score': float(dist)
            })
    return results


def get_context_from_results(results: List[Dict]) -> str:
    """Combine search results into context string for LLM."""
    if not results:
        return ""
    context_parts = []
    for i, result in enumerate(results, 1):
        time_info = ""
        start = result.get('start_time')
        end = result.get('end_time')
        if start is not None and end is not None:
            try:
                time_info = f" [Timestamp: {float(start):.1f}s-{float(end):.1f}s]"
            except (TypeError, ValueError):
                time_info = f" [Timestamp: {start}s-{end}s]"
        context_parts.append(f"[Chunk {result['chunk_index']}{time_info}]: {result['text']}")
    return "\n\n".join(context_parts)


def extract_best_timestamp(results: List[Dict]) -> Optional[float]:
    """
    Extract the most relevant timestamp from search results.
    Returns the start_time of the highest-ranked result that has a valid timestamp.
    """
    for result in results:
        start = result.get('start_time')
        # Only return if it's a valid number > 0
        if start is not None and isinstance(start, (int, float)) and start > 0:
            try:
                return float(start)
            except (TypeError, ValueError):
                continue
    return None  # Return None if no valid timestamp found