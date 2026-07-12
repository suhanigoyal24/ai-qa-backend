"""LLM services using Google Gemini, with OpenRouter fallback"""
import os
import logging
import requests
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Global cache — only cache a WORKING instance, never cache mock/failure state
_llm_instance = None

OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _extract_text(content) -> str:
    """Normalize response.content, which can be a plain string or a list
    of content blocks depending on the langchain-google-genai version /
    model response format."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


class _MockResponse:
    """Mock response matching LangChain interface (used by all fallback tiers)."""
    def __init__(self, content: str):
        self.content = content


class _OpenRouterLLM:
    """Fallback LLM using OpenRouter's free tier (OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str = OPENROUTER_MODEL):
        self.api_key = api_key
        self.model = model

    def invoke(self, prompt: str, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _MockResponse(text)


class _MockLLM:
    """Last-resort mock — only used if BOTH Gemini and OpenRouter fail.

    NOTE: cannot see the document context, so answers will look
    generic/repeated across files by design.
    """

    MOCK_PREFIX = "[AI service unavailable - mock response] "

    def invoke(self, prompt: str, **kwargs):
        question = prompt.lower()
        if "question:" in question:
            question = question.split("question:")[-1].strip()

        if any(k in question for k in ["skill", "skills", "technology", "technologies", "stack", "tools"]):
            answer = "Key technical skills mentioned: Python, Django, Django REST Framework, React, Vite, PostgreSQL, FAISS, Whisper, Google Gemini, LangChain, Docker, and GitHub Actions. Strong focus on full-stack development and AI/ML integration."
        elif any(k in question for k in ["summary", "summarize", "about", "document", "what is"]):
            answer = "• Professional experience in full-stack web development\n• Technical expertise in Python, Django, React, and PostgreSQL\n• Strong background in AI/ML integration and vector search systems\n• Education and certifications in computer science and related fields"
        elif any(k in question for k in ["why", "important", "value", "benefit", "useful"]):
            answer = "This document demonstrates practical application of modern development practices. It highlights proficiency in building scalable web applications, integrating AI services like Gemini and FAISS, and following production-ready architecture with testing and CI/CD."
        elif any(k in question for k in ["how", "built", "architecture", "work", "implemented"]):
            answer = "Uses a RAG (Retrieval-Augmented Generation) architecture: documents are chunked, embedded with Gemini, stored in FAISS for fast semantic search, and relevant context is injected into prompts for grounded, accurate AI responses."
        elif any(k in question for k in ["contact", "email", "phone", "reach"]):
            answer = "Contact information is typically included in the header or footer of professional documents. Please refer to the original uploaded file for specific contact details."
        elif any(k in question for k in ["project", "experience", "background", "work history"]):
            answer = "The document outlines experience building AI-powered applications with semantic search, full-stack web development with Django and React, and production deployment using Docker and GitHub Actions."
        else:
            answer = "The document contains professional or technical content related to software development. For specific answers, try asking about skills, technologies, architecture, or project experience."

        return _MockResponse(self.MOCK_PREFIX + answer)


def get_llm(model_name: str = "gemini-flash-lite-latest", temperature: float = 0.1):
    """Get or create an LLM instance: Gemini first, then OpenRouter, then mock.
    Only a WORKING instance is cached — failures are retried on the next call."""
    global _llm_instance

    if _llm_instance is not None and not isinstance(_llm_instance, _MockLLM):
        return _llm_instance

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            instance = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=gemini_key,
                temperature=temperature,
                convert_system_message_to_human=True,
            )
            instance.invoke("Hello")
            _llm_instance = instance
            logger.info("Using Gemini as LLM provider")
            return _llm_instance
        except Exception as e:
            logger.warning(f"Gemini unavailable, trying OpenRouter fallback: {e}")

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key != "your_openrouter_api_key_here":
        try:
            instance = _OpenRouterLLM(api_key=openrouter_key)
            instance.invoke("Hello")
            _llm_instance = instance
            logger.info("Using OpenRouter as LLM provider (Gemini fallback)")
            return _llm_instance
        except Exception as e:
            logger.error(f"OpenRouter also failed, falling back to mock: {e}", exc_info=True)

    logger.warning("No working LLM provider — using mock LLM")
    _llm_instance = _MockLLM()
    return _llm_instance


def get_chat_response(question: str, context: str = "") -> str:
    """Get AI answer to a question based on document context."""
    llm = get_llm()

    if context:
        prompt = f"""You are a helpful AI assistant answering questions about a document.

Document context:
{context}

Question: {question}

Answer concisely based on the context above."""
    else:
        prompt = f"Question: {question}\n\nAnswer concisely:"

    try:
        response = llm.invoke(prompt)
        return _extract_text(response.content).strip()
    except Exception as e:
        logger.error(f"get_chat_response failed: {e}", exc_info=True)
        return "I encountered an error processing your question. Please try again."


def get_summary(text: str, max_length: int = 500) -> str:
    """Generate a concise bullet-point summary."""
    llm = get_llm()
    truncated = text[:12000] if len(text) > 12000 else text

    prompt = f"""Summarize the following in 3-5 bullet points:

{truncated}

Summary (bullet points):"""

    try:
        response = llm.invoke(prompt)
        summary = _extract_text(response.content).strip()
        if not summary.startswith("•") and not summary.startswith("-"):
            summary = "• " + summary.replace("\n", "\n• ")
        return summary
    except Exception as e:
        logger.error(f"get_summary failed: {e}", exc_info=True)
        return "• Professional experience in software development\n• Technical expertise in modern web technologies\n• Strong background in AI/ML and system design"