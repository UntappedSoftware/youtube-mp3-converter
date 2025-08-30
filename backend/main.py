from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
from asyncio import Semaphore
import os
import uuid
import logging
import time
import random
import requests
from bs4 import BeautifulSoup

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
    
    # Add proxy if it's a yt-dlp call
    if args and 'yt-dlp' in args[0]:
        proxy = get_random_proxy()
        if proxy:
            args = list(args) + ['--proxy', proxy]
            logger.info(f"Added proxy {proxy} to yt-dlp command.")
    
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    
    # Log stderr
    if stderr:
        logger.warning(f"Subprocess stderr: {stderr.decode().strip()}")
    
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
                resultDiv.innerHTML = '';
                spinner.style.display = 'block';

                if (!url) {
                    spinner.style.display = 'none';
                    resultDiv.textContent = 'Please enter a YouTube URL.';
                    return;
                }

                try {
                    // Instead of streaming, use background task
                    const res = await fetch('/start_conversion', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ youtube_url: url })
                    });
                    const data = await res.json();
                    const jobId = data.job_id;

                    // Poll for status and show download button
                    const statusInterval = setInterval(async () => {
                        const statusRes = await fetch(`/job_status/${jobId}`);
                        const statusData = await statusRes.json();
                        if (statusData.status === 'done') {
                            clearInterval(statusInterval);
                            spinner.style.display = 'none';
                            const link = document.createElement('a');
                            link.href = `/download/${jobId}.mp3`;
                            link.className = 'download-btn';
                            link.textContent = 'Download MP3';
                            resultDiv.innerHTML = '<div>Conversion complete:</div>';
                            resultDiv.appendChild(link);
                        } else if (statusData.status === 'error') {
                            clearInterval(statusInterval);
                            spinner.style.display = 'none';
                            resultDiv.textContent = `Error: ${statusData.error}`;
                        }
                    }, 1000); // Check status every 1 second
                } catch (err) {
                    spinner.style.display = 'none';
                    resultDiv.textContent = `Error: ${err.message}`;
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
        logger.info(f"Starting stream conversion for URL: {youtube_url}")

        # Get a random proxy
        proxy = get_random_proxy()
        proxy_flag = ['--proxy', proxy] if proxy else []
        logger.info(f"Using proxy {proxy} for streaming.")

        # Step 1: Get the YouTube stream URL
        stream_url = await run_subprocess(
            "yt-dlp", "-f", "bestaudio", "--no-playlist", "-g", "--cookies", COOKIES_FILE, youtube_url,
            *proxy_flag  # Add proxy flag
        )
        logger.info(f"Stream URL obtained: {stream_url}")

        # Step 2: Use ffmpeg to process the stream and convert it to MP3
        ffmpeg_command = [
            "ffmpeg",
            "-re",               # Read input in real-time
            "-fflags", "nobuffer",  # Minimize buffering
            "-i", stream_url,    # Input is the YouTube stream URL
            "-f", "mp3",         # Output format is MP3
            "-b:a", "96k",       # Lower audio bitrate for faster conversion
            "-vn",               # No video
            "-preset", "ultrafast",  # Use the fastest encoding preset
            "-threads", "8",     # Use 4 threads
            "-flush_packets", "1",  # Flush packets immediately
            "pipe:1"             # Output to stdout (streaming)
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("FFmpeg process started")

        # Step 3: Stream the MP3 output to the user's browser
        async def mp3_stream():
            try:
                total_bytes = 0
                chunk_size = 1048576  # 1 MB chunks (increased for speed)
                while True:
                    chunk = await asyncio.wait_for(process.stdout.read(chunk_size), timeout=10.0)  # 10-second timeout
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    yield chunk
                logger.info(f"Streaming complete. Total bytes: {total_bytes}")
            except asyncio.TimeoutError:
                logger.error("Streaming timed out")
                raise
            except Exception as e:
                logger.error(f"Error during streaming: {str(e)}")
                raise
            finally:
                stderr = await process.stderr.read()
                logger.info(f"FFmpeg stderr: {stderr.decode().strip()}")

        # Set the response headers to trigger a download in the browser
        headers = {
            "Content-Disposition": 'attachment; filename="converted.mp3"',
            "Content-Type": "audio/mpeg",
        }

        return StreamingResponse(mp3_stream(), headers=headers)

    except Exception as e:
        logger.error(f"Stream conversion failed: {str(e)}")
        return {"error": str(e)}

# Add a semaphore to limit concurrent conversions (e.g., 2 at a time)
conversion_semaphore = Semaphore(2)

# Function to fetch proxies from free-proxy-list.net
def fetch_free_proxies():
    """Fetch a list of free proxies from https://free-proxy-list.net/."""
    url = 'https://free-proxy-list.net/'
    proxies = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'table table-striped table-bordered'})
        if not table:
            logging.warning("Proxy table not found on the page.")
            return proxies
        
        rows = table.find_all('tr')[1:]  # Skip header row
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                code = cols[2].text.strip()  # Country code
                anonymity = cols[4].text.strip()  # e.g., anonymous
                https = cols[6].text.strip().lower() == 'yes'  # HTTPS support
                
                # Prefer HTTPS proxies for yt-dlp
                if https:
                    proxy = f'https://{ip}:{port}'
                else:
                    proxy = f'http://{ip}:{port}'
                
                proxies.append(proxy)
        
        logging.info(f"Fetched {len(proxies)} proxies.")
        return proxies[:50]  # Limit to 50 to avoid overload
    except Exception as e:
        logging.error(f"Error fetching proxies: {str(e)}")
        return []

# List of proxies (populate dynamically)
PROXIES = fetch_free_proxies()

def get_random_proxy():
    """Select a random proxy from the list."""
    return random.choice(PROXIES) if PROXIES else None

# Example usage in convert_youtube_to_mp3
async def convert_youtube_to_mp3(youtube_url, job_id):
    async with conversion_semaphore:
        try:
            start_time = time.time()
            logger.info(f"Job {job_id}: Starting conversion process.")

            # Get a random proxy
            proxy = get_random_proxy()
            proxy_flag = ['--proxy', proxy] if proxy else []
            logger.info(f"Job {job_id}: Using proxy {proxy}.")

            # Fetch audio stream URL (optimized with proxy)
            step_start = time.time()
            yt_dlp_process = await asyncio.create_subprocess_exec(
                "yt-dlp", "-f", "bestaudio", "--no-playlist", "-o", "-", "--http-chunk-size", "10M", "--cookies", COOKIES_FILE, youtube_url,
                *proxy_flag,  # Add proxy flag
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info(f"Job {job_id}: yt-dlp process started. Time taken: {time.time() - step_start:.2f} seconds.")

            # Start ffmpeg process (optimized)
            step_start = time.time()
            ffmpeg_process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", "pipe:0", "-f", "mp3", "-b:a", "96k", "-vn",  # Reduced bitrate for speed
                "-preset", "ultrafast", "-threads", "4", f"/tmp/{job_id}.mp3",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info(f"Job {job_id}: ffmpeg process started. Time taken: {time.time() - step_start:.2f} seconds.")

            # Pipe data (optimized)
            step_start = time.time()
            await pipe_streams(yt_dlp_process, ffmpeg_process)
            logger.info(f"Job {job_id}: Data piped in {time.time() - step_start:.2f} seconds.")

            # Wait for ffmpeg to finish
            step_start = time.time()
            await ffmpeg_process.communicate()
            if ffmpeg_process.returncode != 0:
                logger.error(f"Job {job_id}: ffmpeg failed with return code {ffmpeg_process.returncode}")
                conversion_jobs[job_id]["status"] = "error"
                return

            # Check if file was created
            file_path = f"/tmp/{job_id}.mp3"
            if os.path.exists(file_path):
                logger.info(f"Job {job_id}: File created successfully at {file_path}")
                conversion_jobs[job_id]["status"] = "done"
                conversion_jobs[job_id]["download_url"] = f"/download/{job_id}.mp3"
            else:
                logger.error(f"Job {job_id}: File not created at {file_path}")
                conversion_jobs[job_id]["status"] = "error"
                conversion_jobs[job_id]["error"] = "File creation failed"
        except Exception as e:
            logger.error(f"Job {job_id}: Conversion failed: {str(e)}")
            conversion_jobs[job_id]["status"] = "error"
            conversion_jobs[job_id]["error"] = str(e)

async def pipe_streams(yt_dlp_process, ffmpeg_process):
    try:
        logger.info("Starting to pipe data from yt-dlp to ffmpeg.")
        total_bytes = 0
        chunk_size = 1048576  # 1 MB chunks (increased for speed)
        while True:
            chunk = await yt_dlp_process.stdout.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            ffmpeg_process.stdin.write(chunk)
        await ffmpeg_process.stdin.drain()
        ffmpeg_process.stdin.close()
        logger.info(f"Finished piping data. Total bytes transferred: {total_bytes}")
    except Exception as e:
        logger.error(f"Error during piping streams: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    # Fetch proxies on startup
    global PROXIES
    PROXIES = fetch_free_proxies()
    logger.info(f"Loaded {len(PROXIES)} proxies on startup.")
    
    # Optional: Refresh proxies every hour
    import asyncio
    async def refresh_proxies():
        while True:
            await asyncio.sleep(3600)  # 1 hour
            PROXIES = fetch_free_proxies()
            logger.info(f"Refreshed proxies: {len(PROXIES)} available.")
    
    asyncio.create_task(refresh_proxies())

@app.on_event("startup")
async def preload_dependencies():
    logger.info("Preloading yt-dlp and ffmpeg dependencies.")
    await run_subprocess("yt-dlp", "--version")
    await run_subprocess("ffmpeg", "-version")
    logger.info("Dependencies preloaded successfully.")