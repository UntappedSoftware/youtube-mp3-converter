# Use BuildKit for faster builds (run: export DOCKER_BUILDKIT=1)
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Set workdir and install Python deps (copy requirements.txt first for caching)
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Copy ffmpeg and yt-dlp from builder
COPY --from=builder /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/yt-dlp /usr/local/bin/yt-dlp

# Set workdir
WORKDIR /app

# Copy app files (do this last to maximize cache)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
