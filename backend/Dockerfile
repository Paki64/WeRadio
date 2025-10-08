# WeRadio Backend - Dockerfile
# ==============================
# Multi-stage build for production-ready Python Flask application

# Stage 1: Base image with FFmpeg
FROM python:3.13-slim as base

#  dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Build stage
FROM base as builder

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production image
FROM base

# Create non-root user
RUN useradd -m -u 1000 weradio && \
    mkdir -p /app/data/library /app/data/hls_output /app/data/audio_cache && \
    chown -R weradio:weradio /app

# Set working directory
WORKDIR /app

# Python dependencies
COPY --from=builder /root/.local /home/weradio/.local

# Application code
COPY --chown=weradio:weradio . .

# Update PATH for user-installed packages
ENV PATH=/home/weradio/.local/bin:$PATH

# Switch to non-root user
USER weradio

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=2)" || exit 1

# Run the application
CMD ["python", "app.py"]
