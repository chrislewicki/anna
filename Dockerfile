# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio/voice
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libsodium23 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV AUTH_TOKEN=""
ENV DISCORD_TOKEN=""

CMD ["python", "bot.py"]

