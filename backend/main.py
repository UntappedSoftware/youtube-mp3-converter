from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio

COOKIES_FILE = "cookies.txt"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Serve static files (FFmpeg WASM files)
app.mount("/static", StaticFiles(directory="static"), name="static")

async def run_subprocess(*args):
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
    <html lang="en">
    <head>
    ...
    <script type="module">
        import { createFFmpeg, fetchFile } from "/static/ffmpeg/ffmpeg-module.js";

        const ffmpeg = createFFmpeg({
            log: true,
            corePath: "/static/ffmpeg/ffmpeg-core.js",
            progress: ({ ratio }) => {
                if (ratio !== undefined) {
                    const percent = Math.round(ratio * 100);
                    document.getElementById("progressBar").style.width = percent + "%";
                    document.getElementById("status").innerText = "Converting: " + percent + "%";
                }
            },
        });

        const convertBtn = document.getElementById("convertBtn");
        const status = document.getElementById("status");

        convertBtn.onclick = async () => {
            const youtubeURL = document.getElementById("youtubeURL").value.trim();
            if (!youtubeURL) return alert("Please paste a YouTube URL");

            try {
                document.getElementById("progressBar").style.width = "0%";
                status.innerText = "Fetching audio URL from backend...";

                const res = await fetch(`/getVideoUrl?youtube_url=${encodeURIComponent(youtubeURL)}`);
                const data = await res.json();
                if (data.error) throw new Error(data.error);

                status.innerText = `Preparing to convert: "${data.title}"`;

                await ffmpeg.load();

                const audioData = await fetchFile(data.audioUrl);

                ffmpeg.FS("writeFile", "input.audio", audioData);
                await ffmpeg.run("-i", "input.audio", "-q:a", "0", "output.mp3");

                const mp3Data = ffmpeg.FS("readFile", "output.mp3");
                const blob = new Blob([mp3Data.buffer], { type: "audio/mp3" });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = `${data.title}.mp3`;
                a.click();

                status.innerText = `Conversion complete: "${data.title}.mp3"`;
                document.getElementById("progressBar").style.width = "100%";
            } catch (err) {
                console.error(err);
                status.innerText = "Error: " + err.message;
                document.getElementById("progressBar").style.width = "0%";
            }
        };
    </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/getVideoUrl")
async def get_video_url(youtube_url: str = Query(...), fmt: str = "bestaudio"):
    try:
        audio_url = await run_subprocess(
            "yt-dlp", "-f", fmt, "-g", "--cookies", COOKIES_FILE, youtube_url
        )
        title = await run_subprocess(
            "yt-dlp", "--get-title", "--cookies", COOKIES_FILE, youtube_url
        )
        return {"title": title, "audioUrl": audio_url}
    except Exception as e:
        return {"error": str(e)}
