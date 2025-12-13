import os
import re
import threading
import time
import unicodedata

from fastapi import FastAPI
from fastapi.responses import FileResponse
import yt_dlp

# =============================
# App and Constants
# =============================
app = FastAPI()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# =============================
# Utility Functions
# =============================
def ascii_filename(filename):
    """Sanitize filename for HTTP headers (ASCII only)."""
    nfkd = unicodedata.normalize("NFKD", filename)
    only_ascii = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return re.sub(r"[^A-Za-z0-9._-]", "_", only_ascii)


def delete_file_later(file_path, delay=300):
    """Delete a file after a delay (default 5 minutes)."""
    def delete():
        time.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)

    threading.Thread(target=delete, daemon=True).start()


# =============================
# Endpoint
# =============================
@app.get("/youtube/download")
def download_youtube(url):
    """
    Download a YouTube video as MP4 (video + audio merged)
    and return it as a file response.
    """
    output_template = os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s")
    
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)
            # yt_dlp may add the extension if merging
            if not filename.lower().endswith(".mp4"):
                filename = os.path.splitext(filename)[0] + ".mp4"

            if not os.path.exists(filename):
                return {"error": "Failed to download video."}

    except Exception as e:
        return {"error": f"Failed to download video: {str(e)}"}

    delete_file_later(filename)
    safe_filename = ascii_filename(os.path.basename(filename))
    headers = {"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    return FileResponse(filename, filename=safe_filename, headers=headers)
