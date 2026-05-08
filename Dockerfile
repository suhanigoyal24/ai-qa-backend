# ai-qa-app/Dockerfile - FIXED VERSION
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

# Install system dependencies for Whisper + PDF processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Step 1: Upgrade pip + install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Step 2: Install ALL packages EXCEPT whisper first
RUN pip install --no-cache-dir \
    Django==5.2.4 \
    djangorestframework==3.15.2 \
    django-cors-headers==4.4.0 \
    python-decouple==3.8 \
    gunicorn==22.0.0 \
    whitenoise==6.7.0 \
    psycopg2-binary==2.9.9 \
    dj-database-url==2.2.0 \
    langchain==0.2.16 \
    langchain-community==0.2.16 \
    langchain-google-genai==1.0.10 \
    google-generativeai==0.7.2 \
    faiss-cpu==1.8.0.post1 \
    PyPDF2==3.0.1 \
    python-dotenv==1.0.1 \
    requests==2.32.3 \
    pillow==10.4.0 \
    numpy==1.26.4 \
    pytest==8.3.3 \
    pytest-django==4.9.0 \
    pytest-cov==5.0.0 \
    pytest-mock==3.14.0 \
    django-environ==0.11.2

# Step 3: Install whisper LAST with --no-build-isolation (fixes pkg_resources error)
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# Step 4: Install any remaining platform-specific deps
RUN pip install --no-cache-dir python-magic==0.4.27

# Copy project source code
COPY . .

# Create media directory for uploaded files
RUN mkdir -p media faiss_indexes

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Expose HF Spaces required port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/files/')" || exit 1

# Run migrations + start with gunicorn (production-ready)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 120"]