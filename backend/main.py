from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import os
import uuid
import logging
import time

# Path to your exported cookies file (Netscape format)
COOKIES_FILE = "cookies.txt"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

conversion_jobs = {}

async def run_subprocess(*args):
    """Run a subprocess asynchronously and capture stdout/stderr."""
    logger.info(f"Running subprocess: {' '.join(args)}")
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        logger.error(f"Subprocess failed: {stderr.decode().strip()}")
        raise Exception(f"Command failed: {stderr.decode().strip()}")
    logger.info(f"Subprocess output: {stdout.decode().strip()}")
    return stdout.decode().strip()

class ConversionRequest(BaseModel):
    youtube_url: str

@app.post("/start_conversion")
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks):
    try:
        job_id = str(uuid.uuid4())
        logger.info(f"Job {job_id}: Received conversion request for URL: {request.youtube_url}")
        conversion_jobs[job_id] = {"status": "initializing", "progress": 0, "download_url": None, "error": None}

        background_tasks.add_task(convert_youtube_to_mp3, request.youtube_url, job_id)
        logger.info(f"Job {job_id}: Conversion task added to background.")
        return {"job_id": job_id}
    except Exception as e:
        logger.error(f"Error in /start_conversion: {str(e)}")
        return {"error": str(e)}

@app.get("/job_status/{job_id}")
async def job_status(job_id: str):
    job = conversion_jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    return job

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Test YouTube to MP3 Converter</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
            body { background: #f7f7f7; font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; }
            .navbar { position: sticky; top: 0; width: 100%; background: #222; color: #fff; display: flex; align-items: center; justify-content: space-between; padding: 0 32px; height: 64px; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
            .navbar-logo { display: flex; align-items: center; font-size: 1.5em; font-weight: bold; letter-spacing: 1px; }
            .navbar-logo img { height: 38px; margin-right: 12px; }
            .navbar-links a { color: #fff; text-decoration: none; margin-left: 28px; font-size: 1.08em; transition: color 0.2s; }
            .navbar-links a:hover { color: #28a745; }
            .container { max-width: 500px; margin: 60px auto; background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 32px 24px 24px 24px; text-align: center; }
            h1 { color: #222; font-size: 2.1em; margin-bottom: 10px; }
            p { color: #666; font-size: 1.1em; margin-bottom: 24px; }
            input[type="text"] { width: 80%; padding: 12px; font-size: 1em; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 16px; outline: none; transition: border-color 0.2s; }
            input[type="text"]:focus { border-color: #0078d7; }
            button { background: #0078d7; color: #fff; border: none; padding: 12px 32px; font-size: 1em; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
            button:hover { background: #005fa3; }
            #result { margin-top: 28px; font-size: 1.08em; color: #222; word-break: break-all; }
            .download-btn { display: inline-block; margin-top: 12px; background: #28a745; color: #fff; padding: 10px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; transition: background 0.2s; }
            .download-btn:hover { background: #218838; }
            .coffee-btn { display: inline-block; margin-top: 24px; background: #ff813f; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 1.1em; box-shadow: 0 2px 8px rgba(255,129,63,0.15); transition: background 0.2s, box-shadow 0.2s; }
            .coffee-btn:hover { background: #e66b2f; box-shadow: 0 4px 16px rgba(255,129,63,0.25); }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="navbar-logo">
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
            <button onclick="startConversion()">Convert</button>
            <div id="spinner" style="display: none; margin-top: 10px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 100 100" fill="none">
                    <circle cx="50" cy="50" r="40" stroke="#ff69b4" stroke-width="10" stroke-linecap="round" stroke-dasharray="188.4" stroke-dashoffset="0">
                        <animateTransform attributeName="transform" type="rotate" from="0 50 50" to="360 50 50" dur="1s" repeatCount="indefinite" />
                        <animate attributeName="stroke-dashoffset" values="0;188.4" dur="1s" repeatCount="indefinite" />
                    </circle>
                </svg>
            </div>
            <div id="result"></div>
            <a class="coffee-btn" href="https://ko-fi.com/mp3tube" target="_blank">
                ☕ Buy me a coffee
            </a>
        </div>
        <script>
            async function startConversion() {
                const url = document.getElementById('youtube_url').value.trim();
                const resultDiv = document.getElementById('result');
                const spinner = document.getElementById('spinner');
                resultDiv.innerHTML = ''; // Clear previous results
                spinner.style.display = 'block'; // Show the spinner
                console.log('Spinner shown'); // Debugging log

                if (!url) {
                    spinner.style.display = 'none'; // Hide the spinner
                    resultDiv.textContent = 'Please enter a YouTube URL.';
                    return;
                }

                try {
                    // Start the conversion and get the job ID
                    const res = await fetch('/start_conversion', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ youtube_url: url })
                    });
                    const data = await res.json();
                    if (!data.job_id) {
                        throw new Error('Failed to start conversion.');
                    }
                    const jobId = data.job_id;

                    // Poll the job status
                    const pollInterval = 1000; // Reduced from 2000ms
                    const poll = setInterval(async () => {
                        const statusRes = await fetch(`/job_status/${jobId}`);
                        const statusData = await statusRes.json();
                        if (statusData.error) {
                            clearInterval(poll);
                            spinner.style.display = 'none'; // Hide the spinner
                            console.log('Spinner hidden'); // Debugging log
                            resultDiv.innerHTML = `<span style="color:darkred;">Error: ${statusData.error}</span>`;
                            return;
                        }
                        if (statusData.status === 'done') {
                            clearInterval(poll);
                            spinner.style.display = 'none'; // Hide the spinner
                            console.log('Spinner hidden'); // Debugging log
                            const link = document.createElement('a');
                            link.href = statusData.download_url;
                            link.className = 'download-btn';
                            link.textContent = 'Download MP3';
                            link.setAttribute('download', '');
                            resultDiv.innerHTML = '<div>Conversion complete:</div>';
                            resultDiv.appendChild(link);
                        } else if (statusData.status === 'error') {
                            clearInterval(poll);
                            spinner.style.display = 'none'; // Hide the spinner
                            console.log('Spinner hidden'); // Debugging log
                            resultDiv.innerHTML = `<span style="color:darkred;">Conversion failed: ${statusData.error}</span>`;
                        }
                    }, pollInterval);
                } catch (err) {
                    spinner.style.display = 'none'; // Hide the spinner
                    console.log('Spinner hidden'); // Debugging log
                    resultDiv.textContent = `Error starting conversion: ${err.message}`;
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
            "yt-dlp", "-f", "bestaudio", "--no-playlist", "-g", "--cookies", COOKIES_FILE, youtube_url
        );

        # Step 2: Use ffmpeg to process the stream and convert it to MP3
        ffmpeg_command = [
            "ffmpeg",
            "-re",               # Read input in real-time
            "-fflags", "nobuffer",  # Minimize buffering
            "-i", stream_url,    # Input is the YouTube stream URL
            "-f", "mp3",         # Output format is MP3
            "-b:a", "128k",      # Lower audio bitrate for faster conversion
            "-vn",               # No video
            "-preset", "ultrafast",  # Use the fastest encoding preset
            "-threads", "4",         # Use 4 threads (adjust based on your server's CPU cores)
            "-flush_packets", "1",  # Flush packets immediately
            "pipe:1"             # Output to stdout (streaming)
        ];

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        );

        # Step 3: Stream the MP3 output to the user's browser
        async def mp3_stream():
            try:
                while True:
                    chunk = await process.stdout.read(8192)  # Reduce chunk size to 8 KB
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                print(f"Error during streaming: {str(e)}")  # Log any errors
                raise
            finally:
                stderr = await process.stderr.read()
                print(f"FFmpeg stderr: {stderr.decode().strip()}")  # Log FFmpeg errors

        # Set the response headers to trigger a download in the browser
        headers = {
            "Content-Disposition": 'attachment; filename="converted.mp3"',
            "Content-Type": "audio/mpeg",
        };

        return StreamingResponse(mp3_stream(), headers=headers);

    except Exception as e:
        return {"error": str(e)}

async def convert_youtube_to_mp3(youtube_url, job_id):
    try:
        start_time = time.time()
        logger.info(f"Job {job_id}: Starting conversion process.")

        # Fetch audio stream URL
        step_start = time.time()
        yt_dlp_process = await asyncio.create_subprocess_exec(
            "yt-dlp", "-f", "bestaudio", "-o", "-", "--cookies", COOKIES_FILE, youtube_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(f"Job {job_id}: yt-dlp completed in {time.time() - step_start:.2f} seconds.")

        # Start ffmpeg process
        step_start = time.time()
        ffmpeg_process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", "pipe:0", "-f", "mp3", "-b:a", "128k", "-vn", f"/tmp/{job_id}.mp3",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(f"Job {job_id}: ffmpeg started in {time.time() - step_start:.2f} seconds.")

        # Pipe data
        step_start = time.time()
        await pipe_streams()
        logger.info(f"Job {job_id}: Data piped in {time.time() - step_start:.2f} seconds.")

        # Wait for ffmpeg to finish
        step_start = time.time()
        await ffmpeg_process.communicate()
        logger.info(f"Job {job_id}: ffmpeg finished in {time.time() - step_start:.2f} seconds.")

        logger.info(f"Job {job_id}: Total conversion time: {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Job {job_id}: Conversion failed: {str(e)}")
        conversion_jobs[job_id]["status"] = "error"
        conversion_jobs[job_id]["error"] = str(e)

@app.on_event("startup")
async def preload_dependencies():
    await run_subprocess("yt-dlp", "--version")
    await run_subprocess("ffmpeg", "-version")