🤖 AI-Powered Document & Multimedia Q&A

A full-stack web application that lets users upload PDFs, audio, or video files and interact with 
an AI chatbot to ask questions, generate summaries, and navigate to relevant timestamps in media content.
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-5.2.4-green)
![React](https://img.shields.io/badge/React-19-blue)
![Coverage](https://img.shields.io/badge/Coverage-96.30%25-brightgreen)

✨ Features
- 📄 Multi-format upload (PDF, MP3, MP4, WAV)
- 🤖 RAG-powered AI chat grounded in uploaded content
- 📝 One-click AI summarization
- ⏱️ Automatic timestamp extraction for audio/video playback navigation
- 🔍 FAISS semantic vector search for accurate context retrieval
- 🧪 96.30% automated test coverage

🛠️ Tech Stack
Backend: Django 5.2.4, DRF, PostgreSQL, LangChain, Google Gemini, OpenAI Whisper, FAISS  
Frontend: React 19, Vite, Axios  
Infra:Docker, Docker Compose, GitHub Actions CI/CD

📦 Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- FFmpeg (required for audio/video processing)

🚀 Installation & Setup

1. Clone & Backend
git clone https://github.com/suhanigoyal24/ai-qa-backend.git
cd ai-qa-backend
python -m venv venv
venv\Scripts\activate  # Windows | source venv/bin/activate macOS/Linux
pip install -r requirements.txt
python manage.py migrate

2. Frontend
cd ai-qa-frontend
npm install

🏃 Running Instructions
Terminal 1 (Backend):
venv\Scripts\activate
python manage.py runserver 127.0.0.1:8000

Terminal 2 (Frontend):
cd ai-qa-frontend
npm run dev
Open http://localhost:5173 in your browser to interact with the app.


🧪 Testing
venv\Scripts\activate
pytest api/tests/ -v --cov=api --cov-report=term-missing --cov-fail-under=95
38 tests covering models, services, views, and edge cases
External APIs mocked for reliability
Coverage: 96.30% (exceeds 95% requirement)


🐳 Docker Deployment
docker-compose up --build
# Backend: http://localhost:8000
# PostgreSQL: localhost:5432
docker-compose down

📁 Project Structure
├── api/                  # Django app (models, views, serializers, services/)
├── ai-qa-frontend/       # React + Vite UI
├── config/               # Django settings & URLs
├── .github/workflows/    # CI/CD pipeline
├── Dockerfile            # Backend container
├── docker-compose.yml    # Multi-service orchestration
├── requirements.txt      # Python dependencies
└── README.md             # Documentation


🔒 Security Notes
.env, media/, venv/, node_modules/ are gitignored
Rotate API keys regularly
Restrict CORS_ALLOWED_ORIGINS in production
Enable HTTPS & rate limiting before deployment
