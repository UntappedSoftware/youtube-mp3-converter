
-2
Lines changed: 2 additions & 2 deletions
Original file line number	Original file line	Diff line number	Diff line change
@@ -1,15 +1,15 @@
FROM python:3.11-slim

WORKDIR /app

COPY . /app

# Install ffmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    pip install --upgrade pip && \
    pip install fastapi "uvicorn[standard]" yt-dlp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]