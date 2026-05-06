import os
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    """Initialize Gemini model"""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.1,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

def get_chat_response(prompt: str, context: str = "") -> str:
    """Get AI response with context"""
    llm = get_llm()
    full_prompt = f"""
Context from document:
{context}

User Question: {prompt}

Answer concisely based on the context. If the answer is not in the context, say "I couldn't find this information in the document."
"""
    return llm.invoke(full_prompt).content

def get_summary(text: str) -> str:
    """Generate summary of text"""
    llm = get_llm()
    # Truncate if too long (Gemini 1.5 Flash handles 1M tokens, but be safe)
    truncated_text = text[:50000]
    return llm.invoke(f"Summarize this document in 3-4 bullet points:\n\n{truncated_text}").content