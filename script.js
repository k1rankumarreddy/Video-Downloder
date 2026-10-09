// Replace this with your Koyeb URL after deployment.
const API_URL = "https://video-downloder-nbeb.onrender.com";

const videoUrlInput = document.getElementById("videoUrl");
const getVideoBtn = document.getElementById("getVideoBtn");

const message = document.getElementById("message");
const loading = document.getElementById("loading");

const videoResult = document.getElementById("videoResult");
const videoTitle = document.getElementById("videoTitle");
const videoPlatform = document.getElementById("videoPlatform");

const videoPlayer = document.getElementById("videoPlayer");
const downloadBtn = document.getElementById("downloadBtn");


function showMessage(text, type = "error") {
    message.textContent = text;
    message.className = "message " + type;
}


function hideMessage() {
    message.textContent = "";
    message.className = "message hidden";
}


function detectPlatform(url) {
    try {
        const hostname = new URL(url).hostname.toLowerCase();

        if (
            hostname === "youtube.com" ||
            hostname.endsWith(".youtube.com") ||
            hostname === "youtu.be"
        ) {
            return "YouTube";
        }

        if (
            hostname === "instagram.com" ||
            hostname.endsWith(".instagram.com")
        ) {
            return "Instagram";
        }

    } catch {
        return null;
    }

    return null;
}


getVideoBtn.addEventListener("click", async () => {

    hideMessage();

    videoResult.classList.add("hidden");

    videoPlayer.pause();
    videoPlayer.removeAttribute("src");
    videoPlayer.load();

    downloadBtn.removeAttribute("href");

    const url = videoUrlInput.value.trim();

    if (!url) {
        showMessage("Please paste a video URL.");
        return;
    }

    const platform = detectPlatform(url);

    if (!platform) {
        showMessage("Please enter a valid YouTube or Instagram URL.");
        return;
    }

    if (API_URL === "https://video-downloder-nbeb.onrender.com") {
        showMessage("The backend URL has not been configured yet.");
        return;
    }

    loading.classList.remove("hidden");
    getVideoBtn.disabled = true;

    try {
        const response = await fetch(
            `${API_URL}/api/video`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || `Request failed: ${response.status}`
            );
        }

        videoTitle.textContent = data.title;
        videoPlatform.textContent = `Platform: ${data.platform}`;

        const videoFileUrl = new URL(
            data.video_url,
            API_URL
        ).href;

        videoPlayer.src = videoFileUrl;
        downloadBtn.href = videoFileUrl;

        downloadBtn.download = "video.mp4";

        videoResult.classList.remove("hidden");

        showMessage("Video retrieved successfully.", "success");

    } catch (error) {
        console.error("Video request failed:", error);

        showMessage(
            error.message || "Unable to connect to the video server."
        );

    } finally {
        loading.classList.add("hidden");
        getVideoBtn.disabled = false;
    }
});
