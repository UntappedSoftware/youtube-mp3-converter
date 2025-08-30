from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
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

conversion_jobs = {}

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

class ConversionRequest(BaseModel):
    youtube_url: str

@app.post("/start_conversion")
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    conversion_jobs[job_id] = {"status": "initializing", "progress": 0, "download_url": None, "error": None}
    background_tasks.add_task(convert_youtube_to_mp3, request.youtube_url, job_id)
    return {"job_id": job_id}

async def convert_youtube_to_mp3(youtube_url, job_id):
    try:
        mp3_filename = f"{job_id}.mp3"
        mp3_filepath = f"/tmp/{mp3_filename}"
        conversion_jobs[job_id]["status"] = "downloading"
        conversion_jobs[job_id]["progress"] = 10

        # Download and convert to MP3
        await run_subprocess(
            "yt-dlp", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3",
            "-o", mp3_filepath, "--cookies", COOKIES_FILE, youtube_url
        )
        conversion_jobs[job_id]["status"] = "done"
        conversion_jobs[job_id]["progress"] = 100
        conversion_jobs[job_id]["download_url"] = f"/download/{mp3_filename}"
    except Exception as e:
        conversion_jobs[job_id]["status"] = "error"
        conversion_jobs[job_id]["error"] = str(e)

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>YouTube to MP3 Converter</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
            body {
                background: #f7f7f7;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 0;
            }
            .navbar {
                position: sticky;
                top: 0;
                width: 100%;
                background: #222;
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 32px;
                height: 64px;
                z-index: 100;
                box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            }
            .navbar-logo {
                display: flex;
                align-items: center;
                font-size: 1.5em;
                font-weight: bold;
                letter-spacing: 1px;
            }
            .navbar-logo img {
                height: 38px;
                margin-right: 12px;
            }
            .navbar-links a {
                color: #fff;
                text-decoration: none;
                margin-left: 28px;
                font-size: 1.08em;
                transition: color 0.2s;
            }
            .navbar-links a:hover {
                color: #28a745;
            }
            .container {
                max-width: 500px;
                margin: 60px auto;
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                padding: 32px 24px 24px 24px;
                text-align: center;
            }
            h1 {
                color: #222;
                font-size: 2.1em;
                margin-bottom: 10px;
            }
            p {
                color: #666;
                font-size: 1.1em;
                margin-bottom: 24px;
            }
            input[type="text"] {
                width: 80%;
                padding: 12px;
                font-size: 1em;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-bottom: 16px;
                outline: none;
                transition: border-color 0.2s;
            }
            input[type="text"]:focus {
                border-color: #0078d7;
            }
            button {
                background: #0078d7;
                color: #fff;
                border: none;
                padding: 12px 32px;
                font-size: 1em;
                border-radius: 6px;
                cursor: pointer;
                transition: background 0.2s;
            }
            button:hover {
                background: #005fa3;
            }
            #result {
                margin-top: 28px;
                font-size: 1.08em;
                color: #222;
                word-break: break-all;
            }
            .result-title {
                font-weight: bold;
                font-size: 1.15em;
                margin-bottom: 8px;
            }
            .result-link {
                display: block;
                margin: 8px 0;
                color: #0078d7;
                text-decoration: underline;
                word-break: break-all;
            }
            .download-btn {
                display: inline-block;
                margin-top: 12px;
                background: #28a745;
                color: #fff;
                padding: 10px 24px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: bold;
                transition: background 0.2s;
            }
            .download-btn:hover {
                background: #218838;
            }
            .coffee-btn {
                display: inline-block;
                margin-top: 24px;
                background: #ff813f;
                color: #fff;
                padding: 12px 32px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.1em;
                box-shadow: 0 2px 8px rgba(255,129,63,0.15);
                transition: background 0.2s, box-shadow 0.2s;
            }
            .coffee-btn:hover {
                background: #e66b2f;
                box-shadow: 0 4px 16px rgba(255,129,63,0.25);
            }
            .progress-bar-bg {
                width: 80%;
                background: #eee;
                border-radius: 6px;
                margin: 18px auto 0 auto;
                height: 18px;
                position: relative;
                overflow: hidden;
                display: none;
            }
            .progress-bar-fill {
                background: linear-gradient(90deg, #0078d7 0%, #28a745 100%);
                height: 100%;
                width: 0%;
                border-radius: 6px;
                transition: width 0.3s;
            }
            .progress-label {
                position: absolute;
                width: 100%;
                text-align: center;
                top: 0;
                left: 0;
                font-size: 0.95em;
                color: #222;
                line-height: 18px;
            }
            @media (max-width: 600px) {
                .navbar {
                    flex-direction: column;
                    height: auto;
                    padding: 12px 8px;
                }
                .navbar-logo {
                    margin-bottom: 8px;
                }
                .navbar-links a {
                    margin-left: 16px;
                    font-size: 1em;
                }
                .container {
                    padding: 18px 8px 18px 8px;
                }
                input[type="text"] {
                    width: 98%;
                }
                .progress-bar-bg {
                    width: 98%;
                }
            }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="navbar-logo">
                <img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f3a7.svg" alt="Logo" />
                MP3Tube
            </div>
            <div class="navbar-links">
                <a href="#faqs">FAQs</a>
                <a href="#contact">Contact</a>
                <a href="#about">About</a>
            </div>
        </nav>
        <div class="container">
            <h1>YouTube to MP3 Converter</h1>
            <p>Paste a YouTube URL below and click Convert to get the audio and download the MP3 file.</p>
            <input type="text" id="youtube_url" placeholder="https://www.youtube.com/watch?v=VIDEO_ID" />
            <br>
            <button onclick="startStreamingConversion()">Convert</button>
            <div class="progress-bar-bg" id="progressBar">
                <div class="progress-bar-fill" id="progressFill"></div>
                <div class="progress-label" id="progressLabel"></div>
            </div>
            <div id="result"></div>
            <a class="coffee-btn" href="https://ko-fi.com/mp3tube" target="_blank">
                ☕ Buy me a coffee
            </a>
        </div>
        <div id="faqs" class="container" style="margin-top:40px;">
            <h2>FAQs</h2>
            <p><b>Is this free?</b> Yes, this tool is free to use.</p>
            <p><b>How does it work?</b> Paste a YouTube link, click Convert, and download the MP3.</p>
            <p><b>Is my data safe?</b> Yes, we do not store your downloads.</p>
        </div>
        <div id="contact" class="container" style="margin-top:40px;">
            <h2>Contact</h2>
            <p>Email: <a href="mailto:support@example.com">support@example.com</a></p>
        </div>
        <div id="about" class="container" style="margin-top:40px;">
            <h2>About</h2>
            <p>This open-source tool lets you convert YouTube videos to MP3 audio easily and quickly.</p>
        </div>
        <script>
            function showProgress(percent, label) {
                const bar = document.getElementById('progressBar');
                const fill = document.getElementById('progressFill');
                const lbl = document.getElementById('progressLabel');
                bar.style.display = 'block';
                fill.style.transition = 'width 0.5s ease'; // Smooth animation
                fill.style.width = percent + '%';
                lbl.textContent = label || '';
            }
            function hideProgress() {
                document.getElementById('progressBar').style.display = 'none';
                document.getElementById('progressFill').style.width = '0%';
                document.getElementById('progressLabel').textContent = '';
            }
            function startConversionPolling() {
                const url = document.getElementById('youtube_url').value;
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '';
                showProgress(10, 'Starting...');
                fetch('http://164.92.83.107/start_conversion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({youtube_url: url})
                })
                .then(res => res.json())
                .then(data => {
                    if (data.job_id) {
                        pollStatus(data.job_id, resultDiv);
                    } else {
                        hideProgress();
                        resultDiv.innerHTML = '<span style="color:red;">Error starting conversion.</span>';
                    }
                })
                .catch(() => {
                    hideProgress();
                    resultDiv.innerHTML = '<span style="color:red;">Request failed.</span>';
                });
            }

            function pollStatus(job_id, resultDiv) {
                let interval = setInterval(() => {
                    fetch(`/conversion_status/${job_id}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === "error") {
                            hideProgress();
                            resultDiv.innerHTML = `<span style="color:red;">Error: ${data.error}</span>`;
                            clearInterval(interval);
                        } else if (data.status === "done") {
                            hideProgress();
                            resultDiv.innerHTML = `<a class="download-btn" href="${data.download_url}" target="_blank" download>Download MP3</a>`;
                            clearInterval(interval);
                        } else {
                            // Update progress bar and label
                            showProgress(data.progress, `${data.status}...`);
                        }
                    });
                }, 1000);
            }

            function startStreamingConversion() {
                const url = document.getElementById('youtube_url').value;
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '';

                // Trigger the download directly
                const downloadLink = document.createElement('a');
                downloadLink.href = `http://your-droplet-ip/stream_conversion?youtube_url=${encodeURIComponent(url)}`;
                downloadLink.download = 'converted.mp3';
                downloadLink.click();

                // Optionally, show a message while the download starts
                resultDiv.innerHTML = '<span>Conversion started. Your download will begin shortly...</span>';
            }

            function startStreamingDownload() {
                const url = document.getElementById('youtube_url').value;
                const downloadLink = document.createElement('a');
                downloadLink.href = `http://your-droplet-ip/stream_download?youtube_url=${encodeURIComponent(url)}`;
                downloadLink.download = 'converted.mp3';
                downloadLink.click();
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/getVideoUrl")
async def get_video_url(youtube_url: str = Query(...), fmt: str = "bestaudio"):
    try:
        # Get audio URL and title
        audio_url = await run_subprocess(
            "yt-dlp", "-f", fmt, "-g", "--cookies", COOKIES_FILE, youtube_url
        )
        title = await run_subprocess(
            "yt-dlp", "--get-title", "--cookies", COOKIES_FILE, youtube_url
        )

        # Return info only (no MP3 conversion)
        return {"title": title, "audioUrl": audio_url}
    except Exception as e:
        return {"error": str(e)}

@app.get("/download/{mp3_filename}")
async def download_mp3(mp3_filename: str):
    mp3_filepath = f"/tmp/{mp3_filename}"
    if os.path.exists(mp3_filepath):
        return FileResponse(mp3_filepath, media_type="audio/mpeg", filename=mp3_filename)
    return {"error": "File not found"}

@app.get("/stream_conversion")
async def stream_conversion(youtube_url: str):
    try:
        # Step 1: Get the YouTube stream URL
        stream_url = await run_subprocess(
            "yt-dlp", "-f", "bestaudio", "-g", "--cookies", COOKIES_FILE, youtube_url
        );

        # Step 2: Use ffmpeg to process the stream and convert it to MP3
        ffmpeg_command = [
            "ffmpeg",
            "-i", stream_url,  # Input is the YouTube stream URL
            "-f", "mp3",       # Output format is MP3
            "-b:a", "192k",    # Audio bitrate
            "-vn",             # No video
            "pipe:1"           # Output to stdout (streaming)
        ];

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        );

        # Step 3: Stream the MP3 output to the user's browser
        async def mp3_stream():
            while True:
                chunk = await process.stdout.read(1024)  # Read in chunks
                if not chunk:
                    break
                yield chunk

        # Set the response headers to trigger a download in the browser
        headers = {
            "Content-Disposition": 'attachment; filename="converted.mp3"',
            "Content-Type": "audio/mpeg",
        };

        return StreamingResponse(mp3_stream(), headers=headers);

    except Exception as e:
        return {"error": str(e)}