FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    STORAGE_DIR=/app/storage

# Install FFmpeg with libass support, essential system tools, and Google Montserrat fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass9 \
    fonts-montserrat \
    fonts-dejavu-core \
    fontconfig \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache faster-whisper base model in image to prevent runtime network delays
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8', download_root='/app/storage/cache/models')"

# Create essential directory structure
RUN mkdir -p /app/storage/input \
             /app/storage/output \
             /app/storage/cache/videos \
             /app/storage/cache/audio \
             /app/storage/cache/models \
             /app/storage/secrets \
             /app/assets/fonts \
             /app/assets/music

# Copy code and configs
COPY config.yaml /app/config.yaml
COPY assets/ /app/assets/
COPY src/ /app/src/
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

VOLUME ["/app/storage"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py", "--mode", "daemon"]
