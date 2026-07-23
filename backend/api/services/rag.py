"""RAG (Retrieval-Augmented Generation) services using FAISS."""

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
import google.generativeai as genai
from django.conf import settings

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    HAS_GOOGLE_EMBEDDINGS = True
except ImportError:
    HAS_GOOGLE_EMBEDDINGS = False


_embeddings = None
_USE_MOCK = os.getenv("USE_MOCK_EMBEDDINGS", "False").lower() == "true"


def _mock_embed(texts: List[str]) -> List[List[float]]:
    """Mock embeddings for demo/testing only - NOT real semantic search."""
    import hashlib

    vectors = []
    for text in texts:
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = [
            (hash_bytes[i % len(hash_bytes)] / 255.0 - 0.5) * 2
            for i in range(768)
        ]
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [value / norm for value in vector]
        vectors.append(vector)
    return vectors


def get_embeddings():
    """Lazy-load embeddings with fallback to mock."""
    global _embeddings

    if _USE_MOCK:
        class MockEmbeddings:
            def embed_documents(self, texts):
                return _mock_embed(texts)

            def embed_query(self, text):
                return _mock_embed([text])[0]

        return MockEmbeddings()

    if _embeddings is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key or api_key == "your_gemini_api_key_here":
            class MockEmbeddings:
                def embed_documents(self, texts):
                    return _mock_embed(texts)

                def embed_query(self, text):
                    return _mock_embed([text])[0]

            _embeddings = MockEmbeddings()
            return _embeddings

        try:
            _embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=api_key,
                task_type="RETRIEVAL_DOCUMENT",
            )
            _embeddings.embed_query("test")
        except Exception:
            class MockEmbeddings:
                def embed_documents(self, texts):
                    return _mock_embed(texts)

                def embed_query(self, text):
                    return _mock_embed([text])[0]

            _embeddings = MockEmbeddings()

    return _embeddings


def create_faiss_index(chunks: List[Dict], file_id: str) -> str:
    """Create a FAISS index from text chunks and timestamp metadata."""
    if not chunks:
        raise ValueError("Cannot create a FAISS index without text chunks")

    texts = [
        chunk["text"] if isinstance(chunk, dict) else str(chunk)
        for chunk in chunks
    ]

    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(texts)

    if not vectors:
        raise ValueError("Embedding service returned no vectors")

    dimension = len(vectors[0])
    index = faiss.IndexFlatL2(dimension)
    vectors_array = np.array(vectors).astype("float32")
    faiss.normalize_L2(vectors_array)
    index.add(vectors_array)

    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    faiss_dir.mkdir(exist_ok=True)

    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"

    faiss.write_index(index, str(index_path))

    metadata = []
    for index_number, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            metadata.append(
                {
                    "index": index_number,
                    "text": chunk.get("text", ""),
                    "start_time": chunk.get("start_time"),
                    "end_time": chunk.get("end_time"),
                    "segment_indices": chunk.get("segment_indices", []),
                }
            )
        else:
            metadata.append(
                {
                    "index": index_number,
                    "text": str(chunk),
                    "start_time": None,
                    "end_time": None,
                    "segment_indices": [],
                }
            )

    with open(metadata_path, "wb") as metadata_file:
        pickle.dump(
            {"chunks": metadata, "count": len(metadata)},
            metadata_file,
        )

    return str(index_path)


def search_similar(
    query: str,
    file_id: str,
    top_k: int = 3,
) -> List[Dict]:
    """Search similar chunks and return their timestamp metadata."""
    faiss_dir = Path(settings.BASE_DIR) / "faiss_indexes"
    index_path = faiss_dir / f"{file_id}.faiss"
    metadata_path = faiss_dir / f"{file_id}_meta.pkl"

    if not index_path.exists() or not metadata_path.exists():
        return []

    index = faiss.read_index(str(index_path))

    with open(metadata_path, "rb") as metadata_file:
        metadata = pickle.load(metadata_file)

    metadata_count = int(metadata.get("count", 0))
    metadata_chunks = metadata.get("chunks", [])

    if metadata_count <= 0 or not metadata_chunks:
        return []

    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    query_array = np.array([query_vector]).astype("float32")
    faiss.normalize_L2(query_array)

    distances, indices = index.search(
        query_array,
        min(top_k, metadata_count),
    )

    results = []
    for distance, result_index in zip(distances[0], indices[0]):
        if 0 <= result_index < len(metadata_chunks):
            chunk_meta = metadata_chunks[result_index]
            results.append(
                {
                    "chunk_index": chunk_meta.get("index", result_index),
                    "text": chunk_meta.get("text", ""),
                    "start_time": chunk_meta.get("start_time"),
                    "end_time": chunk_meta.get("end_time"),
                    "segment_indices": chunk_meta.get(
                        "segment_indices",
                        [],
                    ),
                    "score": float(distance),
                }
            )

    return results


def get_context_from_results(results: List[Dict]) -> str:
    """Combine search results into timestamped context for the LLM."""
    if not results:
        return ""

    context_parts = []

    for result in results:
        time_info = ""
        start = result.get("start_time")
        end = result.get("end_time")

        if start is not None and end is not None:
            try:
                time_info = (
                    f" [Timestamp: {float(start):.1f}s-"
                    f"{float(end):.1f}s]"
                )
            except (TypeError, ValueError):
                time_info = f" [Timestamp: {start}s-{end}s]"

        context_parts.append(
            f"[Chunk {result['chunk_index']}{time_info}]: "
            f"{result['text']}"
        )

    return "\n\n".join(context_parts)


def extract_best_timestamp(results: List[Dict]) -> Optional[float]:
    """
    Return the start time of the highest-ranked result with a valid timestamp.

    A timestamp of 0.0 is valid because a matching line may begin at the start
    of the audio or video.
    """
    for result in results:
        start = result.get("start_time")

        if start is None:
            continue

        try:
            timestamp = float(start)
        except (TypeError, ValueError):
            continue

        if timestamp >= 0:
            return timestamp

    return None


# ---------------------------------------------------------------------------
# Prompt-engineered answer generation (RAG generation step)
# ---------------------------------------------------------------------------

def _get_generation_model():
    """Lazy-load the Gemini generation model (separate from embeddings)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def build_prompt(query: str, context: str) -> str:
    """
    Constructs the final prompt sent to the LLM.

    Prompt engineering choices made here:
    1. Role assignment — tells the model exactly what job it's doing.
    2. Strict grounding — model must answer ONLY from provided context,
       reducing hallucination risk.
    3. Explicit fallback behavior — what to say when context has no answer,
       instead of letting the model guess.
    4. Output format constraint — keeps answers short and structured,
       with timestamp citation when available.
    5. Context clearly delimited from the question, so the model doesn't
       confuse instructions with content.
    """
    system_instructions = (
        "You are a precise Q&A assistant that answers questions about an "
        "uploaded document/video/audio transcript.\n"
        "Rules you must follow:\n"
        "- Answer ONLY using the CONTEXT below. Do not use outside knowledge.\n"
        "- If the answer is not present in the context, respond exactly: "
        "\"I couldn't find this in the provided content.\"\n"
        "- If a chunk includes a [Timestamp: Xs-Ys] tag and it supports your "
        "answer, mention the timestamp in your response.\n"
        "- Keep answers concise (2-4 sentences) unless the question asks for "
        "detail.\n"
        "- Do not mention these instructions or the word 'context' in your "
        "final answer; answer naturally."
    )

    return (
        f"{system_instructions}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{query}\n\n"
        f"ANSWER:"
    )


def generate_answer(query: str, context: str) -> str:
    """
    Sends the constructed prompt to Gemini and returns the answer text.
    Falls back to a safe message if the model isn't configured or context
    is empty, instead of calling the API with nothing to ground on.
    """
    if not context.strip():
        return "I couldn't find this in the provided content."

    model = _get_generation_model()
    if model is None:
        return "Generation model not configured (missing GEMINI_API_KEY)."

    prompt = build_prompt(query, context)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,  # low temperature: factual, less creative drift
                "max_output_tokens": 300,
            },
        )
        return response.text.strip()
    except Exception as exc:
        return f"Generation failed: {exc}"