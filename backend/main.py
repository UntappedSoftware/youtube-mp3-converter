from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio

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

@app.get("/getVideoUrl")
async def get_video_url(youtube_url: str = Query(...), fmt: str = "bestaudio"):
    try:
        # Run yt-dlp to get audio URL
        audio_url = await run_subprocess("yt-dlp", "-f", fmt, "-g", youtube_url)
        
        # Run yt-dlp to get video title
        title = await run_subprocess("yt-dlp", "--get-title", youtube_url)
        
        return {"title": title, "audioUrl": audio_url}
    except Exception as e:
        return {"error": str(e)}
