---
title: ai-qa-app
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI QA App

Django + RAG + Gemini API powered backend for the AI Questionnaire App. Supports multi-format document ingestion (PDF, image, audio, video) with retrieval-augmented question answering.

## Live Demo

- Frontend: https://ai-qa-frontend.vercel.app
- Backend API: https://gsuhani17-ai-qa-backend.hf.space

## API Endpoints

| Endpoint | Description |
|---|---|
| `/api/health/` | Health check |
| `/api/questions/` | Ask questions against ingested documents |
| `/api/files/` | Upload and manage PDF, image, audio, and video files |

## Tech Stack

- **Backend:** Django 5.2.4, Django REST Framework
- **AI/RAG:** LangChain, Google Gemini API
- **Vector Search:** FAISS
- **Transcription:** OpenAI Whisper
- **Deployment:** Docker, Hugging Face Spaces

## Environment Variables (Secrets)

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `DJANGO_SECRET_KEY` | Django secret key |
| `DEBUG` | Set to False in production |
| `ALLOWED_HOSTS` | Comma-separated allowed domains |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend URLs |

## Local Setup

```bash
git clone https://github.com/suhanigoyal24/ai-qa-app.git
cd ai-qa-app
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