# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps required by PyMuPDF and python-magic
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        libgl1-mesa-glx \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp and log directories
RUN mkdir -p logs

# Run as non-root
RUN useradd -m botuser
USER botuser

CMD ["python", "-m", "bot.main"]
