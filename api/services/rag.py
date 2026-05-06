import os
import faiss
import pickle
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from django.conf import settings

# Initialize embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def create_faiss_index(chunks: list, file_id: str) -> str:
    """Create FAISS index from text chunks and save to disk"""
    # Convert chunks to embeddings
    texts = chunks
    vectors = embeddings.embed_documents(texts)
    
    # Create FAISS index (cosine similarity via L2 norm on normalized vectors)
    dimension = len(vectors[0])
    index = faiss.IndexFlatL2(dimension)
    
    # Normalize vectors for cosine similarity
    import numpy as np
    vectors_array = np.array(vectors).astype('float32')
    faiss.normalize_L2(vectors_array)
    index.add(vectors_array)
    
    # Save index and metadata
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    faiss_dir.mkdir(exist_ok=True)
    
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    faiss.write_index(index, str(index_path))
    
    # Save chunk metadata
    with open(metadata_path, 'wb') as f:
        pickle.dump({'chunks': chunks, 'count': len(chunks)}, f)
    
    return str(index_path)

def search_similar(query: str, file_id: str, top_k: int = 3) -> list:
    """Search for similar chunks using FAISS"""
    import numpy as np
    
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"
    
    if not index_path.exists():
        return []
    
    # Load index
    index = faiss.read_index(str(index_path))
    
    # Load metadata
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)
    
    # Embed query
    query_vector = embeddings.embed_query(query)
    query_array = np.array([query_vector]).astype('float32')
    faiss.normalize_L2(query_array)
    
    # Search
    D, I = index.search(query_array, top_k)
    
    # Return relevant chunks
    results = []
    for idx in I[0]:
        if idx < len(metadata['chunks']):
            results.append({
                'chunk_index': idx,
                'text': metadata['chunks'][idx],
                'score': float(D[0][list(I[0]).index(idx)])
            })
    
    return results

def get_context_from_results(results: list) -> str:
    """Combine search results into context string"""
    if not results:
        return ""
    
    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(f"[Chunk {result['chunk_index']}]: {result['text']}")
    
    return "\n\n".join(context_parts)