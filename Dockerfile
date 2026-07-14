FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=7860

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

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade \
    pip \
    wheel \
    "setuptools==69.5.1"

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p media faiss_indexes

RUN python manage.py collectstatic --noinput --clear

EXPOSE 7860

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]