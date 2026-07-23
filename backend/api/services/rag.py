"""
Prompt-engineered answer generation for the RAG pipeline.
Append this to your existing rag_services.py (or import from here).
"""

import os
import google.generativeai as genai


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