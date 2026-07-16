---
title: ai-qa-app
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI Document Q&A App

A multimodal RAG backend that lets users upload PDFs, images, audio, and video, then ask natural-language questions grounded in the uploaded content.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-5.2.4-092E20)
![Docker](https://img.shields.io/badge/Docker-Hugging%20Face%20Spaces-2496ED)

## Live Demo

- Frontend: https://ai-qa-frontend.vercel.app
- Backend API: https://gsuhani17-ai-qa-backend.hf.space

## Overview

Users upload a document (PDF, image, audio, or video), the backend extracts and chunks its content, embeds it into a FAISS vector index, and answers follow-up questions using retrieval-augmented generation with Google Gemini. Audio and video are transcribed with timestamped segments so answers can reference the exact moment a topic is discussed.

## Features

- Multi-format ingestion: PDF, image, audio, video
- RAG-based question answering grounded in uploaded content
- Timestamp-aware answers for audio/video (points to the relevant moment)
- Automatic bullet-point summaries per file
- JWT authentication with per-user file isolation
- Three-tier LLM fallback: Gemini to OpenRouter to local mock, so the app degrades gracefully instead of failing outright

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Django 5.2.4, Django REST Framework |
| AI / RAG | LangChain, Google Gemini API |
| Vector Search | FAISS |
| Transcription | OpenAI Whisper |
| Database | MySQL (TiDB Cloud) |
| Deployment | Docker, Hugging Face Spaces, Vercel |

## API Endpoints

| Endpoint | Description |
|---|---|
| `/api/health/` | Health check |
| `/api/files/` | Upload and manage PDF, image, audio, and video files |
| `/api/questions/` | Ask questions against ingested documents |
| `/api/auth/login/` | Authenticate and receive a JWT |

## Architecture

```
ai-qa-app/
├── backend/          Django REST API, RAG pipeline, LLM services
│   ├── api/          Views, models, serializers, services
│   └── config/       Django settings, URLs, WSGI
├── frontend/         Static HTML/CSS/JS client
├── Dockerfile         Builds and serves the backend on Hugging Face Spaces
└── README.md
```

## Environment Variables (Secrets)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | Set to False in production |
| `ALLOWED_HOSTS` | Comma-separated allowed domains |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend URLs |
| `DATABASE_URL` | MySQL/TiDB connection string |

## Local Setup

```bash
git clone https://github.com/suhanigoyal24/ai-qa-app.git
cd ai-qa-app/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Author

**Suhani Goyal**
Python Backend Developer | Django | REST APIs

- Email: gsuhani433@gmail.com
- Portfolio: https://suhanigoyal.vercel.app/
- LinkedIn: https://www.linkedin.com/in/suhani-goyal17/
- GitHub: https://github.com/suhanigoyal24