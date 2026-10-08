import os
import uuid
import threading

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory
)

from flask_cors import CORS

import yt_dlp


app = Flask(__name__)

CORS(app)


# Folder where downloaded videos are stored
DOWNLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "downloads"
)

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def detect_platform(url):

    if (
        "youtube.com" in url
        or "youtu.be" in url
    ):
        return "YouTube"

    if "instagram.com" in url:
        return "Instagram"

    return None


def is_instagram(url):

    return "instagram.com" in url


# --------------------------------------------------
# Get Video
# --------------------------------------------------

@app.route(
    "/api/video",
    methods=["POST"]
)
def get_video():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    url = data.get("url", "").strip()


    if not url:

        return jsonify({
            "error": "URL is required."
        }), 400


    platform =
        detect_platform(url)


    if not platform:

        return jsonify({
            "error":
                "Only YouTube and Instagram URLs are supported."
        }), 400


    # ---------------------------------------------
    # Unique ID
    # ---------------------------------------------

    video_id = str(
        uuid.uuid4()
    )


    output_template = os.path.join(
        DOWNLOAD_FOLDER,
        video_id + ".%(ext)s"
    )


    # ---------------------------------------------
    # yt-dlp options
    # ---------------------------------------------

    ydl_opts = {

        "outtmpl":
            output_template,

        "format":
            "bv*+ba/b",

        "merge_output_format":
            "mp4",

        "noplaylist":
            True,

        "quiet":
            True,

        "no_warnings":
            True,

        "restrictfilenames":
            True,

        "max_filesize":
            500 * 1024 * 1024
    }


    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info =
                ydl.extract_info(
                    url,
                    download=True
                )


        # -----------------------------------------
        # Find generated file
        # -----------------------------------------

        possible_files = []

        for filename in os.listdir(
            DOWNLOAD_FOLDER
        ):

            if filename.startswith(
                video_id + "."
            ):

                possible_files.append(
                    filename
                )


        if not possible_files:

            return jsonify({
                "error":
                    "Video was retrieved but the file could not be found."
            }), 500


        filename =
            possible_files[0]


        # -----------------------------------------
        # Title
        # -----------------------------------------

        title = info.get(
            "title",
            "Video"
        )


        # -----------------------------------------
        # Response
        # -----------------------------------------

        return jsonify({

            "success": True,

            "title": title,

            "platform": platform,

            "video_url":
                "/api/video-file/" + filename

        })


    except yt_dlp.utils.DownloadError as e:

        error_text =
            str(e).lower()


        # -----------------------------------------
        # Instagram inaccessible/private
        # -----------------------------------------

        if is_instagram(url):

            if (
                "private" in error_text
                or
                "login required" in error_text
                or
                "requested content is not available"
                in error_text
                or
                "unable to download" in error_text
            ):

                return jsonify({
                    "error":
                        "Account is private or the Instagram video is not publicly accessible."
                }), 403


        return jsonify({
            "error":
                "Unable to retrieve this video. Make sure the URL is valid and the content is publicly accessible."
        }), 400


    except Exception as e:

        print(
            "Server error:",
            str(e)
        )

        return jsonify({
            "error":
                "An unexpected error occurred."
        }), 500


# --------------------------------------------------
# Serve video
# --------------------------------------------------

@app.route(
    "/api/video-file/<filename>",
    methods=["GET"]
)
def video_file(filename):

    return send_from_directory(
        DOWNLOAD_FOLDER,
        filename,
        as_attachment=False
    )


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route(
    "/"
)
def home():

    return jsonify({
        "status": "running",
        "service":
            "Personal Video Downloader"
    })


# --------------------------------------------------
# Start server
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
