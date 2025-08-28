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
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>YouTube to MP3 Converter</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        padding: 20px;
        max-width: 700px;
        margin: auto;
      }
      input {
        width: 80%;
        padding: 10px;
        font-size: 16px;
      }
      button {
        padding: 10px 20px;
        font-size: 16px;
        margin-left: 10px;
      }
      #status {
        margin-top: 20px;
        font-weight: bold;
      }
      #progressContainer {
        width: 100%;
        background-color: #eee;
        border-radius: 5px;
        margin-top: 10px;
        height: 20px;
      }
      #progressBar {
        width: 0%;
        height: 100%;
        background-color: #4caf50;
        border-radius: 5px;
        transition: width 0.2s;
      }
    </style>
  </head>
  <body>
    <h2>YouTube to MP3 Converter</h2>
    <p>Paste a YouTube URL below and download the audio as MP3.</p>
    <input id="youtubeURL" placeholder="Paste YouTube URL here" />
    <button id="convertBtn">Convert to MP3</button>
    <p id="status"></p>

    <div id="progressContainer">
      <div id="progressBar"></div>
    </div>

    <script type="module">
      import { FFmpeg } from "https://cdn.jsdelivr.net/npm/@ffmpeg/ffmpeg/+esm";

      const ffmpeg = new FFmpeg({
        //core: "https://cdn.jsdelivr.net/npm/@ffmpeg.wasm/core-mt/dist/core.min.js",
        log: true,
        progress: ({ ratio }) => {
          if (ratio !== undefined) {
            const percent = Math.round(ratio * 100);
            document.getElementById("progressBar").style.width = percent + "%";
            document.getElementById("status").innerText =
              "Converting: " + percent + "%";
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

          // 1. Get direct audio URL from backend
          const res = await fetch(
            `https://youtube-mp3-converter-hdir.onrender.com/getVideoUrl?youtube_url=${encodeURIComponent(
              youtubeURL
            )}`
          );
          const data = await res.json();
          if (data.error) throw new Error(data.error);

          status.innerText = `Preparing to convert: "${data.title}"`;

          // 2. Load FFmpeg WASM
          //if (!ffmpeg.isLoaded())
          await ffmpeg.load();

          // 3. Fetch audio via CORS proxy
          status.innerText = "Downloading audio stream via proxy...";
          const audioData = await fetchFile(
            `https://your-proxy.onrender.com/proxy?url=${encodeURIComponent(
              data.audioUrl
            )}`
          );

          // Optional: warn if file is large
          if (audioData.byteLength > 50_000_000) {
            const proceed = confirm(
              "The file is large and conversion may take a while. Continue?"
            );
            if (!proceed) {
              status.innerText = "Conversion canceled.";
              return;
            }
          }

          // 4. Write input file for FFmpeg
          ffmpeg.FS("writeFile", "input.audio", audioData);

          // 5. Convert to MP3
          await ffmpeg.run("-i", "input.audio", "-q:a", "0", "output.mp3");

          // 6. Create downloadable MP3 blob
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
