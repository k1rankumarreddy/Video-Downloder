#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Install the official Deno runtime for yt-dlp's YouTube JavaScript challenges.
mkdir -p "$HOME/.deno"
curl -fsSL https://deno.land/install.sh | sh
export PATH="$HOME/.deno/bin:$PATH"

echo "Build dependencies ready."
python -c "import yt_dlp, imageio_ffmpeg; print('yt-dlp:', yt_dlp.version.__version__); print('FFmpeg:', imageio_ffmpeg.get_ffmpeg_exe())"
deno --version
