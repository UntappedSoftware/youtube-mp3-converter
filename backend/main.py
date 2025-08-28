from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/getVideoUrl")
async def get_video_url(youtube_url: str = Query(...)):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-g", youtube_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        audio_url = result.stdout.strip()
        title_result = subprocess.run(
            ["yt-dlp", "--get-title", youtube_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        title = title_result.stdout.strip()
        return {"title": title, "audioUrl": audio_url}
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr}
