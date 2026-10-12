import base64
import binascii
import logging
import mimetypes
import os
import re
import shutil
import tempfile
from urllib.parse import urlparse

import imageio_ffmpeg
import yt_dlp
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)

# Render's native Python runtime may keep Deno in the user's home directory.
deno_dir = os.path.expanduser("~/.deno/bin")
if os.path.isdir(deno_dir) and deno_dir not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = deno_dir + os.pathsep + os.environ.get("PATH", "")

app = Flask(__name__)
app.logger.info("Installed yt-dlp version: %s", yt_dlp.version.__version__)
app.logger.info("FFmpeg executable: %s", imageio_ffmpeg.get_ffmpeg_exe())
app.logger.info("Deno executable found: %s", shutil.which("deno") or "not found")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

FRONTEND_ORIGIN = "https://k1rankumarreddy.github.io"
MAX_VIDEO_BYTES = 100 * 1024 * 1024

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [FRONTEND_ORIGIN],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "expose_headers": ["X-Video-Title", "X-Video-Platform"],
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
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be",
        }
        instagram_hosts = {
            "instagram.com", "www.instagram.com", "m.instagram.com",
        }
        if host in youtube_hosts:
            return "YouTube"
        if host in instagram_hosts:
            return "Instagram"
        return None
    except (TypeError, ValueError):
        return None


def write_optional_youtube_cookies(temp_dir):
    """Read an optional base64-encoded Netscape cookie file from a secret env var.

    Never put cookie contents in source control or logs. Cookies are account
    credentials; use a dedicated account and rotate/remove the secret if exposed.
    """
    encoded = os.environ.get("YOUTUBE_COOKIES_B64", "").strip()
    if not encoded:
        return None

    try:
        cookie_bytes = base64.b64decode(encoded, validate=True)
        cookie_text = cookie_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise RuntimeError(
            "YOUTUBE_COOKIES_B64 is not valid base64-encoded UTF-8 cookie text."
        ) from exc

    if not cookie_text.lstrip().startswith("# Netscape HTTP Cookie File") and not cookie_text.lstrip().startswith("# HTTP Cookie File"):
        raise RuntimeError(
            "YOUTUBE_COOKIES_B64 must contain a Netscape-format cookies.txt file."
        )

    cookie_path = os.path.join(temp_dir, "youtube-cookies.txt")
    with open(cookie_path, "w", encoding="utf-8") as cookie_file:
        cookie_file.write(cookie_text)
    try:
        os.chmod(cookie_path, 0o600)
    except OSError:
        pass
    return cookie_path


def friendly_download_error(exc, platform):
    details = str(exc).lower()
    if "sign in to confirm you're not a bot" in details or "confirm you’re not a bot" in details:
        return (
            "YouTube is blocking requests from this hosting server as automated traffic. "
            "Updating yt-dlp and JavaScript support cannot guarantee a fix for an IP-based block. "
            "If you control the video, check the Render logs and configure a valid cookie secret "
            "only if you are authorized to use that account; otherwise try again later."
        )
    if "private" in details or "login required" in details or "authentication" in details:
        return (
            f"This {platform} video requires access that the server does not have. "
            "Only publicly accessible videos can be retrieved."
        )
    if "ffmpeg" in details:
        return "The media-processing tool could not merge the selected streams. Check the backend deployment logs."
    if "requested format is not available" in details:
        return "No compatible format was available for this video. Try another public video."
    if "429" in details or "too many requests" in details:
        return "The platform is rate-limiting the server. Wait before trying again."
    if "403" in details or "forbidden" in details:
        return "The platform denied the media request. The link may have expired or the server may be blocked."
    return (
        "Could not retrieve this video. It may be unsupported, restricted, too large, "
        "or temporarily unavailable to the server."
    )


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Personal Video Downloader API",
        "health": "/api/health",
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "yt_dlp_version": yt_dlp.version.__version__,
        "deno_available": shutil.which("deno") is not None,
        "ffmpeg_available": os.path.isfile(imageio_ffmpeg.get_ffmpeg_exe()),
        "youtube_cookie_secret_configured": bool(os.environ.get("YOUTUBE_COOKIES_B64")),
    })


@app.route("/api/video", methods=["POST", "OPTIONS"])
def get_video():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    if not isinstance(url, str) or not url.strip():
        return jsonify({"error": "Please provide a video URL."}), 400

    url = url.strip()
    platform = validate_url(url)
    if not platform:
        return jsonify({"error": "Enter a valid HTTPS YouTube or Instagram URL."}), 400

    temp_dir = tempfile.mkdtemp(prefix="video_")
    try:
        output_template = os.path.join(temp_dir, "video.%(ext)s")
        options = {
            "outtmpl": output_template,
            "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
            "merge_output_format": "mp4",
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": False,
            "js_runtimes": {"deno": {}},
            "cachedir": False,
            "socket_timeout": 30,
            "retries": 2,
            "extractor_retries": 2,
            "max_filesize": MAX_VIDEO_BYTES,
        }

        # Cookies are optional and only used for YouTube. Keep them in a
        # per-request temporary file and remove them with the download folder.
        if platform == "YouTube":
            cookie_path = write_optional_youtube_cookies(temp_dir)
            if cookie_path:
                options["cookiefile"] = cookie_path

        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)

        files = [
            os.path.join(temp_dir, name)
            for name in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, name))
            and not name.endswith((".part", ".ytdl", ".txt"))
        ]
        if not files:
            raise RuntimeError("No video file was produced.")

        video_path = max(files, key=os.path.getsize)
        if os.path.getsize(video_path) > MAX_VIDEO_BYTES:
            raise RuntimeError("The video exceeds the 100 MB limit.")

        content_type = mimetypes.guess_type(video_path)[0] or "application/octet-stream"
        title = str(info.get("title") or "Video")
        safe_title = re.sub(r"[^A-Za-z0-9 _.-]", "", title).strip()[:100] or "Video"

        response = send_file(
            video_path,
            mimetype=content_type,
            as_attachment=False,
            download_name=safe_title,
        )
        response.headers["X-Video-Title"] = safe_title
        response.headers["X-Video-Platform"] = platform
        response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return response

    except Exception as exc:
        app.logger.exception("Video processing failed for platform %s", platform)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": friendly_download_error(exc, platform)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
