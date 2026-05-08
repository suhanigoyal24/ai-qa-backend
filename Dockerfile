FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Upgrade pip & install setuptools globally
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install whisper FIRST with --no-build-isolation (fixes pkg_resources error)
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# Install the rest (pip will skip whisper since it's already installed)
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories & collect static
RUN mkdir -p media faiss_indexes
RUN python manage.py collectstatic --noinput --clear

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/files/')" || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 120"]