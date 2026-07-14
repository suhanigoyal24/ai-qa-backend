"""LLM services using Google Gemini, with OpenRouter fallback."""

import logging
import os

import requests
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# Only cache a working provider. Never cache a mock/failure state.
_llm_instance = None

OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _extract_text(content) -> str:
    """
    Normalize response content returned as a string or content-block list.
    """
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
    """Mock response matching the LangChain response interface."""

    def __init__(self, content: str):
        self.content = content


class _OpenRouterLLM:
    """Fallback LLM using OpenRouter's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model: str = OPENROUTER_MODEL,
    ):
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

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return _MockResponse(text)


class _MockLLM:
    """Last-resort response provider when Gemini and OpenRouter fail."""

    MOCK_PREFIX = "[AI service unavailable - mock response] "

    def invoke(self, prompt: str, **kwargs):
        question = prompt.lower()

        if "question:" in question:
            question = question.split("question:")[-1].strip()

        if any(
            keyword in question
            for keyword in [
                "skill",
                "skills",
                "technology",
                "technologies",
                "stack",
                "tools",
            ]
        ):
            answer = (
                "Key technical skills mentioned include Python, Django, "
                "Django REST Framework, FAISS, Whisper, Google Gemini, "
                "LangChain, Docker, and GitHub Actions."
            )
        elif any(
            keyword in question
            for keyword in [
                "summary",
                "summarize",
                "about",
                "document",
                "what is",
            ]
        ):
            answer = (
                "The AI service is temporarily unavailable, so a reliable "
                "document-grounded summary cannot be generated right now."
            )
        elif any(
            keyword in question
            for keyword in ["when", "timestamp", "time", "line", "spoken"]
        ):
            answer = (
                "The AI service is temporarily unavailable. Please retry "
                "before relying on a timestamp answer."
            )
        else:
            answer = (
                "The AI service is temporarily unavailable, so I cannot "
                "provide a reliable document-grounded answer right now."
            )

        return _MockResponse(self.MOCK_PREFIX + answer)


def get_llm(
    model_name: str = "gemini-flash-lite-latest",
    temperature: float = 0.1,
):
    """
    Return a working LLM provider: Gemini, OpenRouter, then local mock.

    Only a working remote provider is cached. Provider failures are retried on
    the next request.
    """
    global _llm_instance

    if _llm_instance is not None and not isinstance(
        _llm_instance,
        _MockLLM,
    ):
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
        except Exception as exc:
            logger.warning(
                "Gemini unavailable, trying OpenRouter fallback: %s",
                exc,
            )

    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if (
        openrouter_key
        and openrouter_key != "your_openrouter_api_key_here"
    ):
        try:
            instance = _OpenRouterLLM(api_key=openrouter_key)
            instance.invoke("Hello")
            _llm_instance = instance
            logger.info("Using OpenRouter as LLM provider")
            return _llm_instance
        except Exception as exc:
            logger.error(
                "OpenRouter failed; using mock response provider: %s",
                exc,
                exc_info=True,
            )

    logger.warning("No working LLM provider; using mock response provider")
    return _MockLLM()


def get_chat_response(question: str, context: str = "") -> str:
    """Answer a question using retrieved document context."""
    llm = get_llm()

    if context:
        prompt = f"""You are a helpful AI assistant answering questions about a document.

Document context:
{context}

Question: {question}

Instructions:
- Answer concisely and only from the supplied document context.
- If the question asks when, where, or at what timestamp a line is spoken,
  include the start timestamp from the most relevant timestamped chunk.
- Never invent a timestamp that is not present in the context.

Answer:"""
    else:
        prompt = (
            f"Question: {question}\n\n"
            "Answer concisely. State clearly when document context is missing."
        )

    try:
        response = llm.invoke(prompt)
        return _extract_text(response.content).strip()
    except Exception as exc:
        logger.error(
            "get_chat_response failed: %s",
            exc,
            exc_info=True,
        )
        return "I encountered an error processing your question. Please try again."


def get_summary(text: str, max_length: int = 500) -> str:
    """Generate a concise bullet-point summary."""
    llm = get_llm()
    truncated = text[:12000] if len(text) > 12000 else text

    prompt = f"""Summarize the following document in 3-5 concise bullet points.
Use only information contained in the document.

Document:
{truncated}

Summary:"""

    try:
        response = llm.invoke(prompt)
        summary = _extract_text(response.content).strip()

        if not summary.startswith("•") and not summary.startswith("-"):
            summary = "• " + summary.replace("\n", "\n• ")

        return summary
    except Exception as exc:
        logger.error(
            "get_summary failed: %s",
            exc,
            exc_info=True,
        )
        return "• AI summary generation is temporarily unavailable."