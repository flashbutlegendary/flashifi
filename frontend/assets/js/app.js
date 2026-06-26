/**
 * FlashiFi — Main Application Controller
 * Handles client state, API integrations, polling, PWA features, and UI transitions.
 */

// Determine API Base dynamically
const API_BASE = window.location.protocol.startsWith("http")
    ? (window.location.port === "8000" || window.location.port === "" ? window.location.origin : `${window.location.protocol}//${window.location.hostname}:8000`)
    : "http://localhost:8000"; // fallback for file:// index.html preview

// Microsoft Clarity Config ID (Only loads in production)
const CLARITY_PROJECT_ID = "xbdvgjey"; // Configurable ID placeholder

/* ── DOM ELEMENTS ───────────────────────────────────────────────────────── */
const queryInput = document.getElementById("queryInput");
const btnSearch = document.getElementById("btnSearch");
const searchIcon = document.getElementById("searchIcon");

const resolvedWrapper = document.getElementById("resolvedWrapper");
const trackCard = document.getElementById("trackCard");
const trackThumbnail = document.getElementById("trackThumbnail");
const trackTitle = document.getElementById("trackTitle");
const trackArtist = document.getElementById("trackArtist");
const trackDuration = document.getElementById("trackDuration");
const trackSize = document.getElementById("trackSize");
const trackPlatformBadge = document.getElementById("trackPlatformBadge");

const configGrid = document.getElementById("configGrid");
const formatSelect = document.getElementById("formatSelect");
const qualitySelect = document.getElementById("qualitySelect");

const downloadContainer = document.getElementById("downloadContainer");
const btnDownload = document.getElementById("btnDownload");

const progressCard = document.getElementById("progressCard");
const progressStage = document.getElementById("progressStage");
const progressPercentage = document.getElementById("progressPercentage");
const progressBarFill = document.getElementById("progressBarFill");
const progressSpeed = document.getElementById("progressSpeed");
const progressEta = document.getElementById("progressEta");

const loadingMsgContainer = document.getElementById("loadingMsgContainer");
const loadingMsgText = document.getElementById("loadingMsgText");

const alertBox = document.getElementById("alertBox");
const alertIcon = document.getElementById("alertIcon");
const alertMessage = document.getElementById("alertMessage");

// Feedback Form & Overlays
const feedbackForm = document.getElementById("feedbackForm");
const inputFeedbackEmail = document.getElementById("feedbackEmail");
const inputFeedbackMessage = document.getElementById("feedbackMessage");
const btnSubmitFeedback = document.getElementById("btnSubmitFeedback");

// Feedback Status overlays
const feedbackSuccessOverlay = document.getElementById("feedbackSuccessOverlay");
const feedbackErrorOverlay = document.getElementById("feedbackErrorOverlay");
const btnSuccessOk = document.getElementById("btnSuccessOk");
const btnErrorOk = document.getElementById("btnErrorOk");

// Support Popup
const supportPopup = document.getElementById("supportPopup");
const btnSupportDismiss = document.getElementById("btnSupportDismiss");

/* ── STATE VARIABLES ────────────────────────────────────────────────────── */
let activeQuery = "";
let currentTaskId = null;
let progressInterval = null;
let loadingMessageInterval = null;
let deferredInstallPrompt = null;

/* ── INITIALIZATION & LISTENERS ─────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    initClarity();
    initPWA();
    setupEventListeners();
});

function setupEventListeners() {
    // Search bindings
    btnSearch.addEventListener("click", performSearch);
    queryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") performSearch();
    });

    // Format auto-switching logic
    formatSelect.addEventListener("change", handleFormatChange);

    // Download binding
    btnDownload.addEventListener("click", startDownloadTask);

    // Feedback Form bindings
    feedbackForm.addEventListener("submit", handleFeedbackSubmit);
    btnSuccessOk.addEventListener("click", () => {
        resetFeedbackForm();
    });
    btnErrorOk.addEventListener("click", () => {
        hideFeedbackStatus();
    });

    // Support popup bindings
    btnSupportDismiss.addEventListener("click", dismissSupportPopup);
}

/* ── SEARCH & METADATA FLOW ─────────────────────────────────────────────── */
async function performSearch() {
    const query = queryInput.value.trim();
    if (!query) {
        showAlert("Please enter a song name or paste a track link.", "error");
        return;
    }

    hideAlert();
    resetSearchUI();
    
    // UI Loading state
    btnSearch.disabled = true;
    searchIcon.className = "fa-solid fa-spinner spinner";
    
    // Cycle funny loading messages
    startLoadingMessages("Searching YouTube...");

    try {
        const response = await fetch(`${API_BASE}/metadata?query=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Failed to retrieve song details. Check the link or query and try again.");
        }

        const meta = data.metadata;
        activeQuery = query;

        // Map values to Track Info Card
        trackThumbnail.src = meta.thumbnail_url || "https://images.unsplash.com/photo-1614680376593-902f74fa0d41?w=300";
        trackTitle.textContent = meta.title;
        trackArtist.textContent = meta.artist;
        trackDuration.innerHTML = `<i class="fa-regular fa-clock"></i> ${meta.duration_formatted}`;
        
        const estSize = meta.estimated_size_mb ? meta.estimated_size_mb.toFixed(1) : "—";
        trackSize.innerHTML = `<i class="fa-regular fa-file-audio"></i> Est: ${estSize} MB`;

        // Configure platform badge icon & text
        setupPlatformBadge(meta.source_platform);

        // Transition UI elements in
        resolvedWrapper.style.display = "flex";
        trackCard.style.display = "block";
        configGrid.style.display = "grid";
        downloadContainer.style.display = "block";
        
        // Auto scroll down to track info on mobile
        resolvedWrapper.scrollIntoView({ behavior: "smooth", block: "nearest" });

    } catch (err) {
        showAlert(err.message, "error");
    } finally {
        stopLoadingMessages();
        btnSearch.disabled = false;
        searchIcon.className = "fa-solid fa-arrow-right";
    }
}

function setupPlatformBadge(platform) {
    let iconClass = "fa-brands fa-youtube";
    let badgeClass = "platform youtube";
    let label = "YouTube";

    if (platform === "spotify") {
        iconClass = "fa-brands fa-spotify";
        badgeClass = "platform spotify";
        label = "Spotify Match";
    } else if (platform === "youtube_music") {
        iconClass = "fa-solid fa-music";
        badgeClass = "platform youtube_music";
        label = "YT Music";
    }

    trackPlatformBadge.className = `badge-item ${badgeClass}`;
    trackPlatformBadge.innerHTML = `<i class="${iconClass}"></i> ${label}`;
}

function handleFormatChange() {
    const fmt = formatSelect.value;
    // Lossless WAV/FLAC can only use Lossless quality; MP3 uses numeric bitrates
    if (fmt === "flac" || fmt === "wav") {
        Array.from(qualitySelect.options).forEach(opt => {
            opt.disabled = (opt.value !== "lossless");
        });
        qualitySelect.value = "lossless";
    } else {
        Array.from(qualitySelect.options).forEach(opt => {
            opt.disabled = (opt.value === "lossless");
        });
        qualitySelect.value = "320"; // Default high-quality MP3
    }
}

/* ── DOWNLOAD & PROGRESS FLOW ───────────────────────────────────────────── */
async function startDownloadTask() {
    btnDownload.disabled = true;
    btnDownload.innerHTML = `<i class="fa-solid fa-spinner spinner"></i> Dispatching task...`;
    hideAlert();

    const format = formatSelect.value;
    const quality = qualitySelect.value;

    startLoadingMessages("Negotiating with the bandwidth gods...");

    try {
        const response = await fetch(`${API_BASE}/download`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                query: activeQuery,
                format: format,
                quality: quality
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to start the download request.");
        }

        currentTaskId = data.task_id;
        showProgressCard();
        startPollingProgress();
        
    } catch (err) {
        showAlert(err.message, "error");
        btnDownload.disabled = false;
        btnDownload.innerHTML = `<i class="fa-solid fa-arrow-down-to-line"></i> Download Audio`;
        stopLoadingMessages();
    }
}

function startPollingProgress() {
    if (progressInterval) clearInterval(progressInterval);

    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/progress/${currentTaskId}`);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "The server could not retrieve the task state.");
            }

            const progress = await response.json();
            updateProgressCard(progress);

            if (progress.stage === "completed") {
                clearInterval(progressInterval);
                stopLoadingMessages();
                triggerFileDownload();
                showAlert("Your audio file has been downloaded successfully!", "success");
                resetActionState();
                triggerSupportPopup();
            } else if (progress.stage === "failed") {
                clearInterval(progressInterval);
                stopLoadingMessages();
                showAlert(progress.message || "An error occurred during transcoding.", "error");
                resetActionState();
            }
        } catch (err) {
            clearInterval(progressInterval);
            stopLoadingMessages();
            showAlert(err.message, "error");
            resetActionState();
        }
    }, 1000);
}

function updateProgressCard(progress) {
    const pct = progress.percentage || 0;
    progressBarFill.style.width = `${pct}%`;
    progressPercentage.textContent = `${Math.round(pct)}%`;

    // Map stages to custom dynamic text & icons
    let stageIcon = "fa-spinner spinner";
    let stageTitle = progress.stage;

    switch (progress.stage) {
        case "preparing":
            stageIcon = "fa-circle-nodes";
            stageTitle = "Preparing System";
            break;
        case "resolving":
            stageIcon = "fa-magnifying-glass-location";
            stageTitle = "Resolving Audio Stream";
            break;
        case "downloading":
            stageIcon = "fa-cloud-arrow-down";
            stageTitle = "Downloading stream";
            break;
        case "converting":
            stageIcon = "fa-arrows-spin spinner";
            stageTitle = "Converting with FFmpeg";
            break;
        case "cleaning":
            stageIcon = "fa-broom";
            stageTitle = "Cleaning Temporary files";
            break;
        case "completed":
            stageIcon = "fa-circle-check";
            stageTitle = "Ready to download";
            break;
        case "failed":
            stageIcon = "fa-circle-exclamation";
            stageTitle = "Task Failed";
            break;
    }

    progressStage.innerHTML = `<i class="fa-solid ${stageIcon}"></i> ${stageTitle}`;
    progressSpeed.innerHTML = `Speed: <span>${progress.speed || "—"}</span>`;
    progressEta.innerHTML = `ETA: <span>${progress.eta || "—"}</span>`;
}

function triggerFileDownload() {
    // Perform standard browser redirect download to request file stream from endpoint
    window.location.href = `${API_BASE}/download/${currentTaskId}`;
}

/* ── INTERACTIVE LOADING MESSAGES ───────────────────────────────────────── */
function startLoadingMessages(initialText) {
    if (loadingMessageInterval) clearInterval(loadingMessageInterval);

    loadingMsgContainer.style.display = "block";
    loadingMsgText.textContent = initialText;

    loadingMessageInterval = setInterval(() => {
        // Fade out
        loadingMsgText.style.opacity = 0;
        
        setTimeout(() => {
            if (window.LOADING_MESSAGES && window.LOADING_MESSAGES.length > 0) {
                const idx = Math.floor(Math.random() * window.LOADING_MESSAGES.length);
                loadingMsgText.textContent = window.LOADING_MESSAGES[idx];
            }
            // Fade in
            loadingMsgText.style.opacity = 1;
        }, 300); // matches fade out time
        
    }, 4500); // cycle message every 4.5 seconds
}

function stopLoadingMessages() {
    if (loadingMessageInterval) clearInterval(loadingMessageInterval);
    loadingMsgContainer.style.display = "none";
}

/* ── UI HELPERS ─────────────────────────────────────────────────────────── */
function showAlert(msg, type) {
    alertBox.style.display = "flex";
    alertMessage.textContent = msg;

    if (type === "error") {
        alertBox.className = "alert-box alert-error";
        alertIcon.className = "fa-solid fa-circle-xmark";
    } else {
        alertBox.className = "alert-box alert-success";
        alertIcon.className = "fa-solid fa-circle-check";
    }
}

function hideAlert() {
    alertBox.style.display = "none";
}

function resetSearchUI() {
    resolvedWrapper.style.display = "none";
    progressCard.style.display = "none";
}

function showProgressCard() {
    progressCard.style.display = "block";
    progressBarFill.style.width = "0%";
    progressPercentage.textContent = "0%";
    progressStage.innerHTML = `<i class="fa-solid fa-spinner spinner"></i> Spawning downloader...`;
    progressSpeed.innerHTML = "Speed: <span>—</span>";
    progressEta.innerHTML = "ETA: <span>—</span>";
}

function resetActionState() {
    btnDownload.disabled = false;
    btnDownload.innerHTML = `<i class="fa-solid fa-arrow-down-to-line"></i> Download Audio`;
}

/* ── MODALS (FEEDBACK & OVERLAYS) ───────────────────────────────────────── */
function openModal(modal) {
    modal.style.display = "flex";
    document.body.style.overflow = "hidden"; // block background scroll
}

function closeModal(modal) {
    modal.style.display = "none";
    document.body.style.overflow = ""; // restore scroll
}

async function handleFeedbackSubmit(event) {
    event.preventDefault();

    const email = inputFeedbackEmail.value.trim();
    const message = inputFeedbackMessage.value.trim();

    if (!message) {
        alert("Feedback message is required.");
        return;
    }

    btnSubmitFeedback.disabled = true;
    btnSubmitFeedback.innerHTML = `<i class="fa-solid fa-spinner spinner"></i> Submitting...`;

    try {
        const response = await fetch("https://formspree.io/f/xbdvgjey", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                email: email || "anonymous@flashifi.com",
                message: message
            })
        });

        if (response.ok) {
            feedbackSuccessOverlay.style.display = "flex";
        } else {
            throw new Error("Failed to send your feedback. Please try again later.");
        }
    } catch (err) {
        feedbackErrorOverlay.style.display = "flex";
    } finally {
        btnSubmitFeedback.disabled = false;
        btnSubmitFeedback.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send Feedback`;
    }
}

function resetFeedbackForm() {
    feedbackForm.reset();
    feedbackSuccessOverlay.style.display = "none";
    feedbackErrorOverlay.style.display = "none";
}

function hideFeedbackStatus() {
    feedbackSuccessOverlay.style.display = "none";
    feedbackErrorOverlay.style.display = "none";
}

/* ── SUPPORT POPUP (THANK YOU POPUP) ────────────────────────────────────── */
function triggerSupportPopup() {
    // Select a random dismiss text from our custom options
    if (window.DISMISS_TEXTS && window.DISMISS_TEXTS.length > 0) {
        const idx = Math.floor(Math.random() * window.DISMISS_TEXTS.length);
        btnSupportDismiss.textContent = window.DISMISS_TEXTS[idx];
    } else {
        btnSupportDismiss.textContent = "Close";
    }

    // Delay pop-up slightly to allow the OS download prompt to pop first
    setTimeout(() => {
        supportPopup.style.display = "block";
    }, 1200);
}

function dismissSupportPopup() {
    supportPopup.style.display = "none";
}

/* ── PWA SUPPORT & SERVICES ─────────────────────────────────────────────── */
function initPWA() {
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("sw.js").then((reg) => {
                console.log("[PWA] Service Worker registered successfully: ", reg.scope);
            }).catch((err) => {
                console.warn("[PWA] Service Worker registration failed: ", err);
            });
        });
    }

    // Capture install prompt
    window.addEventListener("beforeinstallprompt", (e) => {
        e.preventDefault();
        deferredInstallPrompt = e;
        // Optionally show install badge/banner in UI if desired
        console.log("[PWA] Install prompt captured");
    });
}

/* ── MICROSOFT CLARITY ─────────────────────────────────────────────────── */
function initClarity() {
    const host = window.location.hostname;
    // Only run in production (skip local dev hosts)
    if (host !== "localhost" && host !== "127.0.0.1" && !host.startsWith("192.168.")) {
        console.log("[Clarity] Initializing Clarity production analytics");
        (function(c,l,a,r,i,t,y){
            c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
            t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
            y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
        })(window,document,"clarity","script",CLARITY_PROJECT_ID);
    } else {
        console.log("[Clarity] Local environment detected - skipping Clarity analytics setup");
    }
}
