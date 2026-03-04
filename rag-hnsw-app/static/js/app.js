// ===== State =====
let isQuerying = false;

// ===== DOM Ready =====
document.addEventListener("DOMContentLoaded", () => {
    refreshDocList();
    setupDragDrop();
    setupFileInput();
    setupKeyboard();
});

// ===== Drag & Drop =====
function setupDragDrop() {
    const dropZone = document.getElementById("dropZone");

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const files = e.dataTransfer.files;
        for (const file of files) {
            uploadFile(file);
        }
    });

    dropZone.addEventListener("click", () => {
        document.getElementById("fileInput").click();
    });
}

// ===== File Input =====
function setupFileInput() {
    document.getElementById("fileInput").addEventListener("change", (e) => {
        for (const file of e.target.files) {
            uploadFile(file);
        }
        e.target.value = "";
    });
}

// ===== Keyboard =====
function setupKeyboard() {
    document.getElementById("queryInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
}

// ===== Upload =====
async function uploadFile(file) {
    const allowed = [".pdf", ".txt", ".docx", ".csv"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showToast(`Unsupported file type: ${ext}`);
        return;
    }

    showUploadProgress(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            const toastType = [400, 422].includes(res.status) ? "warning" : "error";
            showToast(err.detail || `Upload failed (HTTP ${res.status})`, toastType);
            hideUploadProgress();
            return;
        }

        const data = await res.json();
        showUploadProgress(data.message, true);
        showToast(data.message, "success");
        refreshDocList();
        setTimeout(hideUploadProgress, 3500);
    } catch (err) {
        const msg = err.name === "TypeError"
            ? "Network error: could not reach the server. Is the server running?"
            : (err.message || "Upload failed.");
        showToast(msg, "error");
        hideUploadProgress();
    }
}

function showUploadProgress(msg, complete = false) {
    const el = document.getElementById("uploadProgress");
    const fill = document.getElementById("progressFill");
    const status = document.getElementById("uploadStatus");

    el.classList.add("active");
    status.textContent = msg;

    if (complete) {
        fill.style.width = "100%";
        fill.style.background = "linear-gradient(90deg, #10b981, #34d399)";
    } else {
        fill.style.width = "60%";
        fill.style.background = "linear-gradient(90deg, #38bdf8, #818cf8)";
    }
}

function hideUploadProgress() {
    const el = document.getElementById("uploadProgress");
    const fill = document.getElementById("progressFill");
    el.classList.remove("active");
    fill.style.width = "0%";
}

// ===== Document List =====
async function refreshDocList() {
    try {
        const res = await fetch("/api/documents");
        const data = await res.json();

        const docList = document.getElementById("docList");
        const totalChunks = document.getElementById("totalChunks");
        const emptyState = document.getElementById("emptyState");

        totalChunks.textContent = `${data.total_chunks} chunks`;

        if (data.documents.length === 0) {
            docList.innerHTML = "";
            docList.appendChild(createEmptyState());
            return;
        }

        docList.innerHTML = data.documents.map(doc => `
            <div class="doc-item">
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">${doc.chunk_count} chunks</div>
                </div>
                <button class="btn-delete" onclick="deleteDocument('${escapeHtml(doc.filename)}')" title="Delete document">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        `).join("");
    } catch (err) {
        console.error("Failed to refresh doc list:", err);
        showToast("Failed to load document list. Please refresh the page.", "warning");
    }
}

function createEmptyState() {
    const div = document.createElement("div");
    div.className = "empty-state";
    div.innerHTML = `<p>No documents yet</p><p class="hint">Upload files to get started</p>`;
    return div;
}

// ===== Delete Document =====
async function deleteDocument(filename) {
    if (!confirm(`Delete "${filename}" and all its chunks?`)) return;

    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
            method: "DELETE",
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || `Delete failed (HTTP ${res.status})`, "error");
            return;
        }
        showToast(`"${filename}" has been deleted.`, "success");
        refreshDocList();
    } catch (err) {
        const msg = err.name === "TypeError"
            ? "Network error: could not reach the server."
            : (err.message || "Delete failed.");
        showToast(msg, "error");
    }
}

// ===== Query =====
async function sendQuery() {
    if (isQuerying) return;

    const input = document.getElementById("queryInput");
    const question = input.value.trim();
    if (!question) return;

    // Remove welcome message if present
    const welcome = document.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    appendUserMessage(question);
    input.value = "";
    isQuerying = true;
    document.getElementById("sendBtn").disabled = true;

    showLoading();

    try {
        const res = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        hideLoading();

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            const toastType = res.status === 400 ? "warning" : "error";
            showToast(err.detail || `Query failed (HTTP ${res.status})`, toastType);
            return;
        }

        const data = await res.json();
        appendAssistantMessage(data.answer, data.sources);
    } catch (err) {
        hideLoading();
        const msg = err.name === "TypeError"
            ? "Network error: could not reach the server. Is the server running?"
            : (err.message || "Query failed.");
        showToast(msg, "error");
    } finally {
        isQuerying = false;
        document.getElementById("sendBtn").disabled = false;
        input.focus();
    }
}

// ===== Message Rendering =====
function appendUserMessage(text) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message user-message";
    div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatArea.appendChild(div);
    scrollToBottom();
}

function appendAssistantMessage(answer, sources) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message assistant-message";

    const sourcesHtml = sources.length > 0 ? `
        <details class="sources-section">
            <summary>Sources (${sources.length} references)</summary>
            <div class="source-cards">
                ${sources.map(s => `
                    <div class="source-card">
                        <span class="source-filename">${escapeHtml(s.filename)}</span>
                        <span class="source-meta">Page: ${s.page} | Chunk: ${s.chunk_index}</span>
                        <p class="source-snippet">${escapeHtml(s.snippet)}</p>
                    </div>
                `).join("")}
            </div>
        </details>
    ` : "";

    div.innerHTML = `
        <span class="message-label">Assistant</span>
        <div class="answer-card">
            <div class="answer-text">${renderMarkdown(answer)}</div>
            ${sourcesHtml}
        </div>
    `;

    chatArea.appendChild(div);
    scrollToBottom();
}

// ===== Loading Indicator =====
function showLoading() {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message assistant-message";
    div.id = "loadingMessage";
    div.innerHTML = `
        <span class="message-label">Assistant</span>
        <div class="loading-indicator">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
            <span class="loading-text">Searching documents & generating answer...</span>
        </div>
    `;
    chatArea.appendChild(div);
    scrollToBottom();
}

function hideLoading() {
    const el = document.getElementById("loadingMessage");
    if (el) el.remove();
}

// ===== Toast Notifications =====
const TOAST_ICONS = {
    error:   `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>`,
    warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info:    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

const TOAST_TITLES = {
    error: "Error",
    success: "Success",
    warning: "Warning",
    info: "Info",
};

const TOAST_DURATIONS = {
    error: 7000,
    success: 4000,
    warning: 6000,
    info: 5000,
};

function showToast(msg, type = "error") {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        document.body.appendChild(container);
    }

    const duration = TOAST_DURATIONS[type] || 5000;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${TOAST_ICONS[type]}</div>
        <div class="toast-body">
            <div class="toast-title">${TOAST_TITLES[type]}</div>
            <div class="toast-msg">${escapeHtml(String(msg))}</div>
        </div>
        <button class="toast-close" aria-label="Dismiss">&times;</button>
        <div class="toast-progress"><div class="toast-bar" style="animation-duration:${duration}ms"></div></div>
    `;
    toast.querySelector(".toast-close").addEventListener("click", () => dismissToast(toast));
    container.appendChild(toast);

    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add("toast-show"));
    });

    const timer = setTimeout(() => dismissToast(toast), duration);
    toast.dataset.timer = timer;
}

function dismissToast(toast) {
    clearTimeout(Number(toast.dataset.timer));
    toast.classList.remove("toast-show");
    toast.classList.add("toast-hide");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
}

// ===== Utilities =====
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    const chatArea = document.getElementById("chatArea");
    chatArea.scrollTop = chatArea.scrollHeight;
}

function renderMarkdown(text) {
    // Simple markdown rendering
    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Italic: *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");

    // Inline code: `code`
    html = html.replace(/`(.*?)`/g, "<code>$1</code>");

    // Headers: ### text
    html = html.replace(/^### (.*$)/gm, "<h4>$1</h4>");
    html = html.replace(/^## (.*$)/gm, "<h3>$1</h3>");

    // Unordered lists: - item
    html = html.replace(/^[-*] (.*$)/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");

    // Numbered lists: 1. item
    html = html.replace(/^\d+\. (.*$)/gm, "<li>$1</li>");

    // Line breaks: double newline -> paragraph
    html = html.replace(/\n\n/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");
    html = "<p>" + html + "</p>";

    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, "");
    html = html.replace(/<p>(<h[34]>)/g, "$1");
    html = html.replace(/(<\/h[34]>)<\/p>/g, "$1");
    html = html.replace(/<p>(<ul>)/g, "$1");
    html = html.replace(/(<\/ul>)<\/p>/g, "$1");

    return html;
}

// ===== Global Error Catchers =====
window.addEventListener("unhandledrejection", (e) => {
    const msg = e.reason?.message || String(e.reason) || "An unexpected error occurred.";
    // Don't show chrome devtools or browser-internal errors
    if (msg.includes("Failed to fetch")) {
        showToast("Network error: could not reach the server.", "error");
    } else {
        showToast(msg, "error");
    }
});

window.addEventListener("error", (e) => {
    if (e.filename && !e.filename.includes(location.hostname)) return; // skip third-party
    showToast(`Unexpected error: ${e.message}`, "error");
});
