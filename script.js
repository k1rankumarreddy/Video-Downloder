
const API_BASE_URL = "https://video-downloader-nbeb.onrender.com";

const urlInput = document.getElementById("videoUrl");
const getVideoBtn = document.getElementById("getVideoBtn");
const loading = document.getElementById("loading");
const message = document.getElementById("message");
const videoResult = document.getElementById("videoResult");
const videoTitle = document.getElementById("videoTitle");
const videoPlatform = document.getElementById("videoPlatform");
const videoPlayer = document.getElementById("videoPlayer");
const downloadBtn = document.getElementById("downloadBtn");

let currentVideoObjectUrl = null;

function showMessage(text, type = "error") {
    message.textContent = text;
    message.className = `message ${type}`;
}

function hideMessage() {
    message.textContent = "";
    message.className = "message hidden";
}

function getPlatform(url) {
    try {
        const parsed = new URL(url);

        if (parsed.protocol !== "https:") {
            return null;
        }

        const host = parsed.hostname.toLowerCase();

        const youtubeHosts = [
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be"
        ];

        const instagramHosts = [
            "instagram.com",
            "www.instagram.com",
            "m.instagram.com"
        ];

        if (youtubeHosts.includes(host)) {
            return "YouTube";
        }

        if (instagramHosts.includes(host)) {
            return "Instagram";
        }

        return null;
    } catch {
        return null;
    }
}

function clearPreviousVideo() {
    videoPlayer.pause();
    videoPlayer.removeAttribute("src");
    videoPlayer.load();

    downloadBtn.removeAttribute("href");

    if (currentVideoObjectUrl) {
        URL.revokeObjectURL(currentVideoObjectUrl);
        currentVideoObjectUrl = null;
    }

    videoResult.classList.add("hidden");
}

function getFileExtension(contentType) {
    if (contentType.includes("webm")) return "webm";
    if (contentType.includes("quicktime")) return "mov";
    if (contentType.includes("mp4")) return "mp4";

    return "mp4";
}

getVideoBtn.addEventListener("click", async () => {
    hideMessage();
    clearPreviousVideo();

    const url = urlInput.value.trim();

    if (!url) {
        showMessage("Please paste a video URL.");
        urlInput.focus();
        return;
    }

    const platform = getPlatform(url);

    if (!platform) {
        showMessage(
            "Enter a valid HTTPS YouTube or Instagram URL."
        );
        return;
    }

    if (!API_BASE_URL.startsWith("https://")) {
        showMessage("The backend URL is not configured correctly.");
        return;
    }

    getVideoBtn.disabled = true;
    loading.classList.remove("hidden");

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/video`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ url })
            }
        );

        const contentType =
            response.headers.get("content-type") || "";

        if (!response.ok) {
            let errorMessage = `Server error: ${response.status}`;

            if (contentType.includes("application/json")) {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } else {
                const errorText = await response.text();

                if (errorText) {
                    errorMessage = errorText.slice(0, 250);
                }
            }

            throw new Error(errorMessage);
        }

        if (
            contentType.includes("application/json") ||
            contentType.includes("text/html")
        ) {
            throw new Error(
                "The server did not return a video file. " +
                "Check your backend deployment."
            );
        }

        const videoBlob = await response.blob();

        if (!videoBlob.size) {
            throw new Error("The server returned an empty video.");
        }

        currentVideoObjectUrl =
            URL.createObjectURL(videoBlob);

        const title =
            response.headers.get("X-Video-Title") || "Video";

        const actualPlatform =
            response.headers.get("X-Video-Platform") || platform;

        const extension = getFileExtension(contentType);

        videoTitle.textContent = title;
        videoPlatform.textContent = `Platform: ${actualPlatform}`;

        videoPlayer.src = currentVideoObjectUrl;

        downloadBtn.href = currentVideoObjectUrl;
        downloadBtn.download = `video.${extension}`;

        videoResult.classList.remove("hidden");
        showMessage(
            "Video retrieved successfully. You can preview or download it.",
            "success"
        );
    } catch (error) {
        console.error("Video API request failed:", error);

        if (error instanceof TypeError) {
            showMessage(
                "Cannot connect to the backend. Check that the " +
                "service is running and its CORS settings are correct."
            );
        } else {
            showMessage(error.message || "Unable to retrieve the video.");
        }
    } finally {
        loading.classList.add("hidden");
        getVideoBtn.disabled = false;
    }
});

urlInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        getVideoBtn.click();
    }
});
