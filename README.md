---
title: ai-qa-backend
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 AI QA Backend

Django + RAG + Gemini API powered backend for AI Questionnaire App.

## 🔗 API Endpoints
- Health: `/api/health/`
- Questions: `/api/questions/`
- Files: `/api/files/`

## 🔐 Environment Variables (Secrets)
- `GEMINI_API_KEY`: Google Gemini API key
- `DJANGO_SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Comma-separated allowed domains
- `CORS_ALLOWED_ORIGINS`: Comma-separated frontend URLs

## 🚀 Built with
- Django 5.2.4 + DRF
- LangChain + Google Gemini
- FAISS for vector search
- OpenAI Whisper for audio transcription