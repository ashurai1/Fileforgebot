# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System deps required by pdf2docx (OpenCV)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp and log directories, and user, then fix permissions
RUN mkdir -p logs && useradd -m botuser && chown -R botuser:botuser /app

# Run as non-root
USER botuser

CMD ["python", "-m", "bot.main"]
