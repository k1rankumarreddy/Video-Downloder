import os
import uuid

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp


# =========================================================
# Flask application
# =========================================================

app = Flask(__name__)

# Allow your GitHub Pages frontend to communicate
# with this backend.
#CORS(app)
'''CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://k1rankumarreddy.github.io"
            ]
        }
    },
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"]
)'''

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://k1rankumarreddy.github.io",
                "https://hoppscotch.io"
            ]
        }
    },
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"]
)


# =========================================================
# Download folder
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "downloads"
)

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# Detect platform
# =========================================================

def detect_platform(url):

    url = url.lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"

    if "instagram.com" in url:
        return "Instagram"

    return None


# =========================================================
# Get video
# =========================================================

@app.route("/api/video", methods=["POST"])
def get_video():

    # ---------------------------------------------
    # Read JSON request
    # ---------------------------------------------

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    # ---------------------------------------------
    # Get URL
    # ---------------------------------------------

    url = data.get("url", "").strip()

    if not url:

        return jsonify({
            "error": "Please provide a video URL."
        }), 400


    # ---------------------------------------------
    # Detect platform
    # ---------------------------------------------

    platform = detect_platform(url)

    if not platform:

        return jsonify({
            "error":
                "Only YouTube and Instagram URLs are supported."
        }), 400


    # ---------------------------------------------
    # Create unique filename
    # ---------------------------------------------

    video_id = str(uuid.uuid4())

    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        video_id + ".%(ext)s"
    )


    # ---------------------------------------------
    # yt-dlp configuration
    # ---------------------------------------------

    ydl_opts = {

        "outtmpl": output_template,

        # Prefer MP4-compatible video/audio.
        # Falls back to a single available format.
        "format": "bv*+ba/b",

        # Merge video and audio into MP4 when possible.
        "merge_output_format": "mp4",

        # Do not download playlists.
        "noplaylist": True,

        # Keep server output clean.
        "quiet": True,

        "no_warnings": True,

        # Safer filenames.
        "restrictfilenames": True,

        # Maximum file size: 500 MB.
        "max_filesize": 500 * 1024 * 1024
    }


    # =====================================================
    # Download
    # =====================================================

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )


        # ---------------------------------------------
        # Find downloaded file
        # ---------------------------------------------

        downloaded_file = None

        for filename in os.listdir(
            DOWNLOAD_FOLDER
        ):

            if filename.startswith(
                video_id + "."
            ):

                downloaded_file = filename
                break


        if not downloaded_file:

            return jsonify({
                "error":
                    "The video was retrieved, but the downloaded file could not be found."
            }), 500


        # ---------------------------------------------
        # Video title
        # ---------------------------------------------

        title = info.get(
            "title",
            "Video"
        )


        # ---------------------------------------------
        # Return result to frontend
        # ---------------------------------------------

        return jsonify({

            "success": True,

            "title": title,

            "platform": platform,

            "video_url":
                "/api/video-file/" + downloaded_file
        })


    # =====================================================
    # Download error
    # =====================================================

    except yt_dlp.utils.DownloadError as error:

        error_text = str(error).lower()

        print(
            "yt-dlp error:",
            str(error)
        )


        # ---------------------------------------------
        # Instagram inaccessible/private content
        # ---------------------------------------------

        if platform == "Instagram":

            private_or_unavailable = (

                "private" in error_text

                or

                "login required" in error_text

                or

                "requested content is not available"
                in error_text

                or

                "content is not available"
                in error_text

                or

                "unable to download"
                in error_text
            )


            if private_or_unavailable:

                return jsonify({
                    "error":
                        "Account is private or the Instagram video is not publicly accessible."
                }), 403


        # ---------------------------------------------
        # General error
        # ---------------------------------------------

        return jsonify({
            "error":
                "Unable to retrieve this video. Make sure the URL is valid and the content is publicly accessible."
        }), 400


    # =====================================================
    # Unexpected error
    # =====================================================

    except Exception as error:

        print(
            "Server error:",
            str(error)
        )

        return jsonify({
            "error":
                "An unexpected server error occurred."
        }), 500


# =========================================================
# Serve downloaded video
# =========================================================

@app.route(
    "/api/video-file/<path:filename>",
    methods=["GET"]
)
def video_file(filename):

    return send_from_directory(
        DOWNLOAD_FOLDER,
        filename,
        as_attachment=False
    )


# =========================================================
# Health check
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({

        "status": "running",

        "service":
            "Personal Video Downloader",

        "message":
            "Backend is working."
    })


# =========================================================
# Start server
# =========================================================

if __name__ == "__main__":

    # Hosting platforms normally provide PORT
    # through an environment variable.
    #
    # If PORT doesn't exist, use 5000 locally.

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port
    )
