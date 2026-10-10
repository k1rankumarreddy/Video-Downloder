
import os
import re
import shutil
import tempfile
import logging
import mimetypes
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

logging.basicConfig(level=logging.INFO)

FRONTEND_ORIGIN = "https://k1rankumarreddy.github.io"

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [FRONTEND_ORIGIN],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "expose_headers": [
                "X-Video-Title",
                "X-Video-Platform"
            ],
        }
    },
)


def validate_url(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme != "https":
            return None

        host = (parsed.hostname or "").lower()

        youtube_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
        }

        instagram_hosts = {
            "instagram.com",
            "www.instagram.com",
            "m.instagram.com",
        }

        if host in youtube_hosts:
            return "YouTube"

        if host in instagram_hosts:
            return "Instagram"

        return None

    except Exception:
        return None


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Personal Video Downloader API",
        "health": "/api/health"
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/video", methods=["POST", "OPTIONS"])
def get_video():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    url = data.get("url", "")

    if not isinstance(url, str) or not url.strip():
        return jsonify({
            "error": "Please provide a video URL."
        }), 400

    url = url.strip()
    platform = validate_url(url)

    if not platform:
        return jsonify({
            "error": (
                "Enter a valid HTTPS YouTube or Instagram URL."
            )
        }), 400

    temp_dir = tempfile.mkdtemp(prefix="video_")

    try:
        output_template = os.path.join(
            temp_dir, "video.%(ext)s"
        )

        options = {
            "outtmpl": output_template,
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "cachedir": False,
            "socket_timeout": 20,
            "retries": 1,
            "extractor_retries": 1,
            "max_filesize": 100 * 1024 * 1024,
        }

        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(
                url,
                download=True
            )

        files = [
            os.path.join(temp_dir, name)
            for name in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, name))
        ]

        if not files:
            raise RuntimeError("No video file was produced.")

        video_path = max(files, key=os.path.getsize)

        if os.path.getsize(video_path) > 100 * 1024 * 1024:
            raise RuntimeError(
                "The video exceeds the 100 MB limit."
            )

        content_type = (
            mimetypes.guess_type(video_path)[0]
            or "application/octet-stream"
        )

        title = str(info.get("title") or "Video")
        safe_title = re.sub(
            r"[^A-Za-z0-9 _.-]", "",
            title
        ).strip()[:100] or "Video"

        response = send_file(
            video_path,
            mimetype=content_type,
            as_attachment=False,
            download_name=safe_title
        )

        response.headers["X-Video-Title"] = safe_title
        response.headers["X-Video-Platform"] = platform

        # Remove the temporary file after the response is sent.
        response.call_on_close(
            lambda: shutil.rmtree(
                temp_dir, ignore_errors=True
            )
        )

        return response

    except Exception:
        app.logger.exception("Video processing failed")
        shutil.rmtree(temp_dir, ignore_errors=True)

        return jsonify({
            "error": (
                "Could not retrieve this video. It may be "
                "unsupported, restricted, too large, or "
                "unavailable to the server."
            )
        }), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
