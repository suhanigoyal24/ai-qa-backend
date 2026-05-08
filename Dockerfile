# ai-qa-app/Dockerfile - HF Spaces Optimized
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

# Install Python dependencies + fix for whisper build
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

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