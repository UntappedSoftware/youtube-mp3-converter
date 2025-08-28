from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import os
import uuid

# Path to your exported cookies file (Netscape format)
COOKIES_FILE = "cookies.txt"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

async def run_subprocess(*args):
    """Run a subprocess asynchronously and capture stdout/stderr."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Command failed: {stderr.decode().strip()}")
    return stdout.decode().strip()

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Audio URL API</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
            input, button { padding: 10px; font-size: 16px; margin: 5px; }
            #result { margin-top: 20px; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>YouTube Audio URL API</h1>
        <p>Paste a YouTube URL below to get the audio URL and title:</p>
        <input type="text" id="youtube_url" placeholder="https://www.youtube.com/watch?v=VIDEO_ID" size="50"/>
        <button onclick="getAudioUrl()">Get Audio URL</button>
        <div id="result"></div>

        <script>
            async function getAudioUrl() {
                const url = document.getElementById('youtube_url').value;
                const resultDiv = document.getElementById('result');
                resultDiv.textContent = 'Loading...';
                try {
                    const response = await fetch(`/getVideoUrl?youtube_url=${encodeURIComponent(url)}`);
                    const data = await response.json();
                    if(data.error){
                        resultDiv.textContent = 'Error: ' + data.error;
                    } else {
                        resultDiv.innerHTML = 
                            'Title: ' + data.title + '<br>' + 
                            'Audio URL: <a href="' + data.audioUrl + '" target="_blank">' + data.audioUrl + '</a>';
                    }
                } catch (err) {
                    resultDiv.textContent = 'Request failed: ' + err;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/getVideoUrl")
async def get_video_url(youtube_url: str = Query(...), fmt: str = "bestaudio"):
    try:
        # Generate a unique filename for the MP3
        unique_id = str(uuid.uuid4())
        mp3_filename = f"{unique_id}.mp3"
        mp3_filepath = f"/tmp/{mp3_filename}"

        # Get audio URL and title
        audio_url = await run_subprocess(
            "yt-dlp", "-f", fmt, "-g", "--cookies", COOKIES_FILE, youtube_url
        )
        title = await run_subprocess(
            "yt-dlp", "--get-title", "--cookies", COOKIES_FILE, youtube_url
        )

        # Download and convert to MP3
        await run_subprocess(
            "yt-dlp", "-x", "--audio-format", "mp3", "--output", mp3_filepath,
            "--cookies", COOKIES_FILE, youtube_url
        )

        # Return info and download link
        download_url = f"/download/{mp3_filename}"
        return {"title": title, "audioUrl": audio_url, "mp3DownloadUrl": download_url}
    except Exception as e:
        return {"error": str(e)}

@app.get("/download/{mp3_filename}")
async def download_mp3(mp3_filename: str):
    mp3_filepath = f"/tmp/{mp3_filename}"
    if os.path.exists(mp3_filepath):
        return FileResponse(mp3_filepath, media_type="audio/mpeg", filename=mp3_filename)
    return {"error": "File not found"}