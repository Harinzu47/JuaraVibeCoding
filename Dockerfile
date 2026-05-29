# =======================================================================
# Stage 1: Build Frontend React App
# =======================================================================
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# =======================================================================
# Stage 2: builder — install semua Python dependencies
# =======================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools untuk psycopg2, WeasyPrint, asyncpg, dll.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# =======================================================================
# Stage 3: runtime — image final yang ringan
# =======================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy hanya runtime libraries yang dibutuhkan WeasyPrint + asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages dari builder
COPY --from=builder /install /usr/local

# Copy source code (hormat .dockerignore — .env tidak masuk)
COPY . .

# Copy compiled frontend dari stage frontend-builder
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Cloud Run inject PORT via env var — default 8080
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Jalankan migration lalu start Uvicorn
# Shell form agar $PORT ter-expand dengan benar
CMD alembic upgrade head && \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --no-access-log

