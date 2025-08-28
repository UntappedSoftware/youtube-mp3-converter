from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio

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
        # Use cookies file to bypass bot detection
        audio_url = await run_subprocess(
            "yt-dlp", "-f", fmt, "-g", "--cookies", COOKIES_FILE, youtube_url
        )
        title = await run_subprocess(
            "yt-dlp", "--get-title", "--cookies", COOKIES_FILE, youtube_url
        )
        return {"title": title, "audioUrl": audio_url}
    except Exception as e:
        return {"error": str(e)}