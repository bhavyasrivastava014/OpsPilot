# Backend Dockerfile (FastAPI + Uvicorn)
# - Reads configuration from environment variables (no secrets committed).

FROM python:3.11-slim

WORKDIR /app

# System deps needed for PyMuPDF (pymupdf) to work well
# Keep this minimal; if your environment lacks libs, Render might require extra apt packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY app ./app

# Default envs (override on Render)
ENV PORT=8000
ENV VECTORSTORE_BASE_DIR=app/vectorstores

EXPOSE 8000

# Uvicorn expects the app at app.main:app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

