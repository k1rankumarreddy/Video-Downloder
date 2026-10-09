
import os
import uuid

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

FRONTEND_ORIGIN = "https://k1rankumarreddy.github.io"

# Apply CORS to API routes, including video-file requests.
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [FRONTEND_ORIGIN]
        }
    },
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
    max_age=600,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Personal Video Downloader",
        "message": "Backend is working."
    })


@app.route("/api/video", methods=["POST", "OPTIONS"])
def get_video():
    # Explicitly answer browser preflight requests.
    if request.method == "OPTIONS":
        return "", 204

    print("DEBUG: /api/video reached", flush=True)
    print("DEBUG: Origin:", request.headers.get("Origin"), flush=True)

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON request."}), 400

    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "Please provide a video URL."}), 400

    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        platform = "YouTube"
    elif "instagram.com" in url_lower:
        platform = "Instagram"
    else:
        return jsonify({
            "error": "Only YouTube and Instagram URLs are supported."
        }), 400

    video_id = str(uuid.uuid4())
    output_template = os.path.join(
        DOWNLOAD_FOLDER, video_id + ".%(ext)s"
    )

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "max_filesize": 500 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        downloaded_file = next(
            (
                filename for filename in os.listdir(DOWNLOAD_FOLDER)
                if filename.startswith(video_id + ".")
            ),
            None,
        )

        if not downloaded_file:
            return jsonify({
                "error": "Downloaded file could not be found."
            }), 500

        return jsonify({
            "success": True,
            "title": info.get("title", "Video"),
            "platform": platform,
            "video_url": "/api/video-file/" + downloaded_file,
        })

    except yt_dlp.utils.DownloadError as error:
        print("yt-dlp error:", str(error), flush=True)
        return jsonify({
            "error": "Unable to retrieve this video. Check the URL and access permissions."
        }), 400

    except Exception as error:
        print("Server error:", repr(error), flush=True)
        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500


@app.route("/api/video-file/<path:filename>", methods=["GET"])
def video_file(filename):
    if os.path.basename(filename) != filename:
        return jsonify({"error": "Invalid filename."}), 400

    return send_from_directory(
        DOWNLOAD_FOLDER,
        filename,
        as_attachment=False,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
