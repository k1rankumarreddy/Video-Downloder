import os
import uuid

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

FRONTEND_ORIGIN = "https://k1rankumarreddy.github.io"

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [FRONTEND_ORIGIN],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    },
    always_send=True,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def detect_platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"

    if "instagram.com" in url:
        return "Instagram"

    return None


@app.route("/api/video", methods=["POST", "OPTIONS"])
def get_video():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Please provide a video URL."}), 400

    platform = detect_platform(url)

    if not platform:
        return jsonify({
            "error": "Only YouTube and Instagram URLs are supported."
        }), 400

    video_id = str(uuid.uuid4())

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        video_id + ".%(ext)s"
    )

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 500 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        downloaded_file = next(
            (
                name for name in os.listdir(DOWNLOAD_FOLDER)
                if name.startswith(video_id + ".")
            ),
            None
        )

        if not downloaded_file:
            return jsonify({
                "error": "Downloaded video file was not found."
            }), 500

        return jsonify({
            "success": True,
            "title": info.get("title", "Video"),
            "platform": platform,
            "video_url": "/api/video-file/" + downloaded_file,
        })

    except Exception as error:
        app.logger.exception("Video retrieval failed")

        return jsonify({
            "error": "Unable to retrieve this video. Check that the URL is valid and publicly accessible."
        }), 400


@app.route("/api/video-file/<path:filename>", methods=["GET", "OPTIONS"])
def video_file(filename):
    if request.method == "OPTIONS":
        return "", 204

    return send_from_directory(DOWNLOAD_FOLDER, filename)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Personal Video Downloader",
        "message": "Backend is working.",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
