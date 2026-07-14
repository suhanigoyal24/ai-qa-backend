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
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
# Step 1: Pin setuptools to older version that has pkg_resources working correctly
RUN pip install --no-cache-dir "setuptools==69.5.1" wheel pip --upgrade
# Step 2: Install all packages except whisper
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
# Step 3: Install whisper with pinned setuptools already in place
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117
# Step 4: Remaining deps
RUN pip install --no-cache-dir python-magic==0.4.27
COPY . .
RUN mkdir -p media faiss_indexes
# Skip collectstatic if it fails during build (secrets not available at build time)
RUN python manage.py collectstatic --noinput --clear || echo "collectstatic skipped"
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/files/')" || exit 1
# Run collectstatic again at startup when env vars are available, then migrate and serve
CMD ["sh", "-c", "echo '--- Starting migrate ---' && python manage.py migrate --noinput && echo '--- Migrate done, starting gunicorn ---' && gunicorn config.wsgi:application --bind 0.0.0.0:7860 --workers 2 --timeout 300 --access-logfile - --error-logfile - --log-level info"]