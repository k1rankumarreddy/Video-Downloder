const API_URL = "https://video-downloader-nbeb.onrender.com";


const videoUrlInput =
    document.getElementById("videoUrl");

const getVideoBtn =
    document.getElementById("getVideoBtn");

const downloadBtn =
    document.getElementById("downloadBtn");

const videoPlayer =
    document.getElementById("videoPlayer");

const videoResult =
    document.getElementById("videoResult");

const videoTitle =
    document.getElementById("videoTitle");

const videoPlatform =
    document.getElementById("videoPlatform");

const loading =
    document.getElementById("loading");

const message =
    document.getElementById("message");


let currentVideoUrl = null;


/*
    Detect platform
*/

function detectPlatform(url) {

    if (
        url.includes("youtube.com") ||
        url.includes("youtu.be")
    ) {
        return "YouTube";
    }

    if (
        url.includes("instagram.com")
    ) {
        return "Instagram";
    }

    return null;
}


/*
    Show message
*/

function showMessage(text, type = "error") {

    message.textContent = text;

    message.className =
        "message " + type;
}


/*
    Hide message
*/

function hideMessage() {

    message.className =
        "message hidden";

    message.textContent = "";
}


/*
    Get Video
*/

getVideoBtn.addEventListener(
    "click",
    async function () {

        const url =
            videoUrlInput.value.trim();

        hideMessage();

        videoResult.classList.add("hidden");

        videoPlayer.removeAttribute("src");

        currentVideoUrl = null;


        if (!url) {

            showMessage(
                "Please paste a YouTube or Instagram URL."
            );

            return;
        }


        const platform =
            detectPlatform(url);


        if (!platform) {

            showMessage(
                "Please enter a valid YouTube or Instagram URL."
            );

            return;
        }


        loading.classList.remove("hidden");

        getVideoBtn.disabled = true;


        try {
            console.log("Sending request to:", `${API_URL}/api/video`);
            const response =
                await fetch(
                    `${API_URL}/api/video`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            url: url
                        })
                    }
                    );
            console.log("Response received:", response.status);
            const responseText = await response.text();

let data;

try {
    data = JSON.parse(responseText);
} catch (error) {
    console.error("Unexpected server response:", responseText);

    throw new Error(
        `Server returned HTML or invalid JSON. HTTP status: ${response.status}`
    );
}


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "Unable to retrieve video."
                );
            }


            /*
                Backend returns video URL
            */

            currentVideoUrl =
                API_URL + data.video_url;


            videoPlayer.src =
                currentVideoUrl;


            videoTitle.textContent =
                data.title || "Video";


            videoPlatform.textContent =
                data.platform || platform;


            videoResult.classList.remove(
                "hidden"
            );


            showMessage(
                "Video is ready.",
                "success"
            );

        }

        catch (error) {

            console.error(error);

            showMessage(
                error.message ||
                "Something went wrong."
            );

        }

        finally {

            loading.classList.add(
                "hidden"
            );

            getVideoBtn.disabled =
                false;
        }

    }
);


/*
    Download
*/

downloadBtn.addEventListener(
    "click",
    async function () {

        if (!currentVideoUrl) {

            showMessage(
                "No video available."
            );

            return;
        }


        try {

            const response =
                await fetch(
                    currentVideoUrl
                );


            if (!response.ok) {

                throw new Error(
                    "Download failed."
                );
            }


            const blob =
                await response.blob();


            const blobUrl =
                URL.createObjectURL(blob);


            const a =
                document.createElement("a");


            a.href = blobUrl;

            a.download =
                "video.mp4";


            document.body.appendChild(a);

            a.click();

            a.remove();


            URL.revokeObjectURL(
                blobUrl
            );

        }

        catch (error) {

            console.error(error);

            showMessage(
                "Unable to download the video."
            );
        }

    }
);


/*
    Allow Enter key
*/

videoUrlInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            getVideoBtn.click();

        }

    }
);
