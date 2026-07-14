FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860 \
    DJANGO_SETTINGS_MODULE=config.settings

RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/certs && \
    curl -fsSL \
    https://letsencrypt.org/certs/isrgrootx1.pem \
    -o /app/certs/ca-cert.pem

COPY requirements.txt .

# Install a setuptools version that still includes pkg_resources
RUN pip install --no-cache-dir --upgrade \
    pip \
    wheel \
    "setuptools==69.5.1"

# Install application dependencies except Whisper
RUN pip install --no-cache-dir \
    Django==5.2.4 \
    djangorestframework==3.15.2 \
    djangorestframework-simplejwt==5.5.1 \
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
    django-environ==0.11.2 \
    mysqlclient==2.2.8

# Install Whisper separately without build isolation
RUN pip install --no-cache-dir \
    --no-build-isolation \
    openai-whisper==20231117

RUN pip install --no-cache-dir \
    python-magic==0.4.27

COPY . .

RUN mkdir -p media faiss_indexes

# Secrets may not be available during the Docker build
RUN python manage.py collectstatic --noinput --clear || \
    echo "collectstatic skipped during build"


EXPOSE 7860

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug"]