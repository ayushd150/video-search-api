from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp, os, json, tempfile

app = FastAPI(title="Smart Video Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    video_url: str
    topic: str

class AskResponse(BaseModel):
    timestamp: str
    video_url: str
    topic: str

def seconds_to_hhmmss(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_transcript(video_url: str):
    temp_dir = tempfile.gettempdir()
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "json3",
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        video_id = info["id"]
        subtitles = (
            info.get("requested_subtitles")
            or info.get("subtitles")
            or info.get("automatic_captions")
        )
        if not subtitles:
            raise HTTPException(status_code=400, detail="No subtitles available for this video.")
        lang = list(subtitles.keys())[0]
        subtitle_path = os.path.join(temp_dir, f"{video_id}.{lang}.json3")
    if not os.path.exists(subtitle_path):
        raise HTTPException(status_code=400, detail="Subtitle file not found.")
    with open(subtitle_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    os.remove(subtitle_path)
    return data

# =========================
# MAIN ENDPOINT
# =========================

@app.api_route("/ask", methods=["POST"], response_model=AskResponse)
@app.api_route("/ask/", methods=["POST"], response_model=AskResponse)
def ask_video(data: AskRequest):
    transcript_data = get_transcript(data.video_url)
    topic = data.topic.lower()

    for event in transcript_data.get("events", []):
        if "segs" not in event:
            continue
        text = "".join(seg.get("utf8", "") for seg in event["segs"])
        if topic in text.lower():
            start_time = event.get("tStartMs", 0) / 1000
            timestamp = seconds_to_hhmmss(start_time)
            return AskResponse(
                timestamp=timestamp,
                video_url=data.video_url,
                topic=data.topic
            )

    raise HTTPException(status_code=404, detail="Topic not found in transcript.")