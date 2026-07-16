FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=7860 \
    WHISPER_CACHE_DIR=/app/.cache/whisper

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/certs && \
    curl -fsSL \
    https://letsencrypt.org/certs/isrgrootx1.pem \
    -o /app/certs/ca-cert.pem

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --upgrade \
    pip \
    wheel \
    "setuptools==69.5.1"

# Install the CPU-only PyTorch build.
# This prevents Hugging Face CPU Basic from downloading CUDA/NVIDIA packages.
RUN pip install --no-cache-dir \
    torch==2.12.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# Download the Whisper tiny model while building the image.
# It will not need to download the 72 MB model during the first upload.
RUN mkdir -p "${WHISPER_CACHE_DIR}" && \
    python -c "import os, whisper; whisper.load_model('tiny', download_root=os.environ['WHISPER_CACHE_DIR'], device='cpu')"

COPY backend/ .

RUN mkdir -p \
    media \
    faiss_indexes \
    staticfiles

RUN python manage.py collectstatic --noinput --clear

EXPOSE 7860

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 900 --access-logfile - --error-logfile - --log-level info"]