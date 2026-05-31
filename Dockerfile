# ----------------- Base Stage -----------------
# This stage installs common dependencies needed by all services.
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# Install only the non-CV requirements first
RUN pip install --upgrade pip && \
    pip install -r requirements.txt \
    --no-deps fastapi uvicorn pydantic pydantic-settings SQLAlchemy asyncpg redis alembic structlog python-json-logger orjson pytest pytest-asyncio httpx aiosqlite PyYAML numpy python-dotenv

# ----------------- Worker Stage -----------------
# This stage builds on the base and adds the heavy CV libraries.
FROM base as worker

# Copy requirements again and install only the CV-related packages
COPY requirements.txt ./
RUN pip install -r requirements.txt --no-deps ultralytics supervision opencv-python-headless

COPY app ./app

# ----------------- Final API/Migrate Stage -----------------
# This is the final, lean image for the api and migrate services.
FROM base as final

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
