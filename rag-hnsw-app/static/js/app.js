// ============================================================
// State
// ============================================================
let isQuerying    = false;
let currentSessionId = null;   // active chat session id

// ============================================================
// DOM Ready
// ============================================================
document.addEventListener("DOMContentLoaded", async () => {
    setupDragDrop();
    setupFileInput();
    setupKeyboard();
    await refreshDocList();
    await refreshSessions();
    await refreshChatMemory();
});

// ============================================================
// Keyboard — Enter to send, Shift+Enter for newline
// ============================================================
function setupKeyboard() {
    const ta = document.getElementById("queryInput");
    ta.addEventListener("input", () => {
        ta.style.height = "auto";
        ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    });
    ta.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
}

// ============================================================
// Drag & Drop / File Input
// ============================================================
function setupDragDrop() {
    const dropZone = document.getElementById("dropZone");
    dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
    dropZone.addEventListener("dragleave", ()  => { dropZone.classList.remove("drag-over"); });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        for (const file of e.dataTransfer.files) uploadFile(file);
    });
    dropZone.addEventListener("click", () => document.getElementById("fileInput").click());
}

function setupFileInput() {
    document.getElementById("fileInput").addEventListener("change", (e) => {
        for (const file of e.target.files) uploadFile(file);
        e.target.value = "";
    });
}

// ============================================================
// Upload
// ============================================================
const ALLOWED = [".pdf", ".txt", ".docx", ".csv", ".md"];

async function uploadFile(file) {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ALLOWED.includes(ext)) { showToast(`Unsupported file type: ${ext}`, "warning"); return; }

    showUploadProgress(`Uploading ${file.name}…`);
    const form = new FormData();
    form.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: form });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || `Upload failed (HTTP ${res.status})`, [400,422].includes(res.status) ? "warning" : "error");
            hideUploadProgress(); return;
        }
        const data = await res.json();
        showUploadProgress(data.message, true);
        showToast(data.message, "success");
        await refreshDocList();
        setTimeout(hideUploadProgress, 3500);
    } catch (err) {
        showToast(err.name === "TypeError" ? "Network error — is the server running?" : (err.message || "Upload failed."), "error");
        hideUploadProgress();
    }
}

function showUploadProgress(msg, complete = false) {
    const el   = document.getElementById("uploadProgress");
    const fill = document.getElementById("progressFill");
    const stat = document.getElementById("uploadStatus");
    el.classList.add("active");
    stat.textContent = msg;
    fill.style.width    = complete ? "100%" : "60%";
    fill.style.background = complete
        ? "linear-gradient(90deg, #10b981, #34d399)"
        : "linear-gradient(90deg, #38bdf8, #818cf8)";
}

function hideUploadProgress() {
    document.getElementById("uploadProgress").classList.remove("active");
    document.getElementById("progressFill").style.width = "0%";
}

// ============================================================
// Document List (with cross-chat toggles)
// ============================================================
async function refreshDocList() {
    try {
        const res  = await fetch("/api/documents");
        const data = await res.json();
        const list = document.getElementById("docList");
        document.getElementById("totalChunks").textContent = `${data.total_chunks} chunks`;

        if (data.documents.length === 0) {
            list.innerHTML = `<div class="empty-state"><p>No documents yet</p><p class="hint">Upload files to get started</p></div>`;
            updateCrossMemBadge(0); return;
        }

        const sharedCount = data.documents.filter(d => d.is_shared).length;
        updateCrossMemBadge(sharedCount);

        list.innerHTML = data.documents.map(doc => `
            <div class="doc-item ${doc.is_shared ? 'is-shared' : ''}" id="docitem-${CSS.escape(doc.filename)}">
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">${doc.chunk_count} chunks${doc.is_shared ? ' ...· cross-chat' : ''}</div>
                </div>
                <div class="doc-actions">
                    <label class="cross-chat-toggle" title="Share across all chats">
                        <input type="checkbox" ${doc.is_shared ? 'checked' : ''}
                               onchange="toggleDocumentShared('${escapeHtml(doc.filename)}', this.checked)">
                        <span class="toggle-track"><span class="toggle-thumb"></span></span>
                    </label>
                    <button class="btn-delete" onclick="deleteDocument('${escapeHtml(doc.filename)}')" title="Delete document">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Failed to refresh doc list:", err);
        showToast("Could not load document list. Please refresh.", "warning");
    }
}

function updateCrossMemBadge(count) {
    const el = document.getElementById("sharedDocCount");
    if (el) el.textContent = count;
}

// ============================================================
// Cross-Chat Document Toggle
// ============================================================
async function toggleDocumentShared(filename, shared) {
    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}/shared`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ shared }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Failed to update sharing.", "error");
            await refreshDocList(); return;
        }
        showToast(
            shared ? `"${filename}" is now shared across all chats.` : `"${filename}" is no longer shared.`,
            "info",
        );
        await refreshDocList();
    } catch (err) {
        showToast(err.message || "Network error.", "error");
        await refreshDocList();
    }
}

// ============================================================
// Delete Document
// ============================================================
async function deleteDocument(filename) {
    if (!confirm(`Delete "${filename}" and all its chunks?`)) return;
    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || `Delete failed (HTTP ${res.status})`, "error"); return;
        }
        showToast(`"${filename}" deleted.`, "success");
        await refreshDocList();
    } catch (err) {
        showToast(err.message || "Delete failed.", "error");
    }
}

// ============================================================
// Session Management
// ============================================================
async function refreshSessions() {
    try {
        const res  = await fetch("/api/sessions");
        const data = await res.json();
        renderSessionList(data.sessions);

        // Auto-select most recent or the current
        if (data.sessions.length > 0 && !currentSessionId) {
            await selectSession(data.sessions[0].id, false);
        }
    } catch (err) {
        console.error("Failed to fetch sessions:", err);
    }
}

function renderSessionList(sessions) {
    const list = document.getElementById("sessionList");
    if (sessions.length === 0) {
        list.innerHTML = `<div class="empty-state"><p>No chats yet</p><p class="hint">Click "New Chat" to begin</p></div>`;
        return;
    }
    list.innerHTML = sessions.map(s => `
        <div class="session-item ${s.id === currentSessionId ? 'active' : ''}"
             onclick="selectSession('${s.id}', true)"
             id="sess-${s.id}">
            <svg class="session-icon" width="13" height="13" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <div class="session-info">
                <div class="session-title">${escapeHtml(s.title)}</div>
                <div class="session-meta">${s.message_count} messages</div>
            </div>
            <div class="session-actions">
                <button class="btn-session-archive" title="Archive to Inter-Chat Memory"
                        onclick="event.stopPropagation(); archiveSession('${s.id}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <ellipse cx="12" cy="5" rx="9" ry="3"/>
                        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                    </svg>
                </button>
                <button class="btn-session-action danger" title="Delete chat"
                        onclick="event.stopPropagation(); deleteSession('${s.id}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        </div>
    `).join("");
}

async function createNewChat() {
    try {
        const res     = await fetch("/api/sessions", { method: "POST" });
        const session = await res.json();
        currentSessionId = session.id;
        showWelcome();
        updateChatTitle("New Chat");
        await refreshSessions();
    } catch (err) {
        showToast("Could not create a new chat.", "error");
    }
}

async function selectSession(sessionId, loadMessages = true) {
    currentSessionId = sessionId;

    // Highlight in list
    document.querySelectorAll(".session-item").forEach(el => el.classList.remove("active"));
    const item = document.getElementById(`sess-${sessionId}`);
    if (item) item.classList.add("active");

    if (!loadMessages) return;

    try {
        const res  = await fetch(`/api/sessions/${sessionId}`);
        const data = await res.json();
        renderSessionMessages(data.messages);
        const title = document.querySelector(`#sess-${sessionId} .session-title`)?.textContent || "Chat";
        updateChatTitle(title);
    } catch (err) {
        console.error("Failed to load session:", err);
        showWelcome();
    }
}

function renderSessionMessages(messages) {
    const chatArea = document.getElementById("chatArea");
    chatArea.innerHTML = "";

    if (!messages || messages.length === 0) {
        showWelcome(); return;
    }

    for (const msg of messages) {
        if (msg.role === "user") {
            appendUserMessage(msg.content, false);
        } else if (msg.role === "assistant") {
            appendAssistantMessage(msg.content, [], [], false);
        }
    }
    scrollToBottom();
}

async function archiveSession(sessionId) {
    try {
        const res = await fetch(`/api/sessions/${sessionId}/archive`, { method: "POST" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Archive failed.", "error"); return;
        }
        showToast("Chat archived to Inter-Chat Memory.", "success");
        await refreshChatMemory();
    } catch (err) {
        showToast(err.message || "Archive failed.", "error");
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Delete this chat and its history?")) return;
    try {
        await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (currentSessionId === sessionId) {
            currentSessionId = null;
            showWelcome();
            updateChatTitle("RAG Document Assistant");
        }
        await refreshSessions();
        await refreshChatMemory();   // deletion auto-archives the session
        showToast("Chat deleted and archived to memory.", "success");
    } catch (err) {
        showToast("Could not delete chat.", "error");
    }
}

// ============================================================
// Query
// ============================================================
async function sendQuery() {
    if (isQuerying) return;
    const input    = document.getElementById("queryInput");
    const question = input.value.trim();
    if (!question) return;

    // Remove welcome message
    const welcome = document.querySelector(".welcome-message");
    if (welcome) welcome.remove();

    appendUserMessage(question);
    input.value = "";
    input.style.height = "auto";
    isQuerying = true;
    document.getElementById("sendBtn").disabled = true;
    showLoading();

    try {
        const res = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, session_id: currentSessionId }),
        });

        hideLoading();

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || `Query failed (HTTP ${res.status})`, res.status === 400 ? "warning" : "error");
            return;
        }

        const data = await res.json();

        // Update session id in case a new one was auto-created
        if (data.session_id && data.session_id !== currentSessionId) {
            currentSessionId = data.session_id;
        }

        appendAssistantMessage(data.answer, data.sources, data.cross_chat_refs || []);
        await refreshSessions();   // refresh titles + message counts
    } catch (err) {
        hideLoading();
        showToast(err.name === "TypeError" ? "Network error — is the server running?" : (err.message || "Query failed."), "error");
    } finally {
        isQuerying = false;
        document.getElementById("sendBtn").disabled = false;
        input.focus();
    }
}

// ============================================================
// Message Rendering
// ============================================================
function showWelcome() {
    const chatArea = document.getElementById("chatArea");
    chatArea.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
            </div>
            <h3>Start a New Conversation</h3>
            <p>Upload documents in the sidebar, then ask questions. Every answer is grounded in your files.</p>
            <div class="feature-grid">
                <div class="feature-card"><strong>Chat Memory</strong><p>Conversation history is remembered within each chat session</p></div>
                <div class="feature-card"><strong>Cross-Chat Docs</strong><p>Toggle the switch on any document to share it across all sessions</p></div>
                <div class="feature-card"><strong>Hybrid Search</strong><p>HNSW vector similarity + BM25 keyword search fused together</p></div>
                <div class="feature-card"><strong>Source Citations</strong><p>Every answer links back to exact document chunks</p></div>
            </div>
        </div>
    `;
}

function updateChatTitle(title) {
    const el = document.getElementById("chatTitle");
    if (el) el.textContent = title;
}

function appendUserMessage(text, scroll = true) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message user-message";
    div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatArea.appendChild(div);
    if (scroll) scrollToBottom();
}

function appendAssistantMessage(answer, sources = [], crossChatRefs = [], scroll = true) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message assistant-message";

    const sourcesHtml = sources && sources.length > 0 ? `
        <details class="sources-section">
            <summary>Sources (${sources.length} reference${sources.length !== 1 ? 's' : ''})</summary>
            <div class="source-cards">
                ${sources.map(s => `
                    <div class="source-card">
                        <span class="source-filename">${escapeHtml(s.filename)}</span>
                        <span class="source-meta">Page: ${s.page} &middot; Chunk: ${s.chunk_index}</span>
                        <p class="source-snippet">${escapeHtml(s.snippet)}</p>
                    </div>
                `).join("")}
            </div>
        </details>
    ` : "";

    const refsHtml = crossChatRefs && crossChatRefs.length > 0 ? `
        <details class="cross-chat-refs">
            <summary>Inter-Chat Memory used (${crossChatRefs.length} past session${crossChatRefs.length !== 1 ? 's' : ''})</summary>
            <div class="cross-chat-ref-cards">
                ${crossChatRefs.map(r => `
                    <div class="cross-chat-ref-card">
                        <div class="ref-session-title">${escapeHtml(r.session_title)}</div>
                        <div class="ref-session-meta">${r.archived_at}</div>
                        <p class="ref-snippet">${escapeHtml(r.snippet)}</p>
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
            ${refsHtml}
        </div>
    `;
    chatArea.appendChild(div);
    if (scroll) scrollToBottom();
}

// ============================================================
// Inter-Chat Memory
// ============================================================
async function refreshChatMemory() {
    try {
        const res  = await fetch("/api/chat-memory");
        const data = await res.json();
        renderMemoryList(data.entries || []);
        updateMemoryBadge(data.total || 0);
    } catch (err) {
        console.error("Failed to refresh chat memory:", err);
    }
}

function renderMemoryList(entries) {
    const list = document.getElementById("memoryList");
    if (!list) return;
    if (entries.length === 0) {
        list.innerHTML = `<div class="empty-state"><p>No memories yet</p><p class="hint">Delete or archive a chat to save it here</p></div>`;
        return;
    }
    list.innerHTML = entries.map(e => `
        <div class="memory-item" id="mem-${e.session_id}">
            <div class="memory-item-header">
                <div class="memory-title" title="${escapeHtml(e.session_title)}">${escapeHtml(e.session_title)}</div>
                <button class="btn-memory-delete" title="Delete memory"
                        onclick="deleteChatMemoryEntry('${e.session_id}')">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <div class="memory-meta">${e.archived_at ? e.archived_at.slice(0,10) : ''} &middot; ${e.message_count} msgs</div>
            <p class="memory-snippet">${escapeHtml(e.summary)}</p>
        </div>
    `).join("");
}

function updateMemoryBadge(count) {
    const el1 = document.getElementById("memoryCount");
    if (el1) el1.textContent = count;
    const el2 = document.getElementById("memoryBadgeCount");
    if (el2) el2.textContent = count;
}

async function deleteChatMemoryEntry(sessionId) {
    if (!confirm("Remove this memory entry?")) return;
    try {
        const res = await fetch(`/api/chat-memory/${sessionId}`, { method: "DELETE" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Delete failed.", "error"); return;
        }
        showToast("Memory entry deleted.", "success");
        await refreshChatMemory();
    } catch (err) {
        showToast(err.message || "Delete failed.", "error");
    }
}

// ============================================================
// Loading Indicator
// ============================================================
function showLoading() {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message assistant-message";
    div.id = "loadingMessage";
    div.innerHTML = `
        <span class="message-label">Assistant</span>
        <div class="loading-indicator">
            <div class="loading-dots"><span></span><span></span><span></span></div>
            <span class="loading-text">Searching documents &amp; generating answer…</span>
        </div>
    `;
    chatArea.appendChild(div);
    scrollToBottom();
}

function hideLoading() {
    const el = document.getElementById("loadingMessage");
    if (el) el.remove();
}

// ============================================================
// Toast Notifications
// ============================================================
const TOAST_ICONS = {
    error:   `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
    success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="9 12 11 14 15 10"/></svg>`,
    warning: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info:    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};
const TOAST_TITLES    = { error: "Error", success: "Success", warning: "Warning", info: "Info" };
const TOAST_DURATIONS = { error: 7000, success: 4000, warning: 6000, info: 5000 };

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
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("toast-show")));
    toast.dataset.timer = setTimeout(() => dismissToast(toast), duration);
}

function dismissToast(toast) {
    clearTimeout(Number(toast.dataset.timer));
    toast.classList.remove("toast-show");
    toast.classList.add("toast-hide");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
}

// ============================================================
// Utilities
// ============================================================
function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}

function scrollToBottom() {
    const chatArea = document.getElementById("chatArea");
    chatArea.scrollTop = chatArea.scrollHeight;
}

function renderMarkdown(text) {
    let html = escapeHtml(text);

    // Fenced code blocks ```lang ... ```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="lang-${lang || 'text'}">${code.trimEnd()}</code></pre>`;
    });

    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Italic *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Headers
    html = html.replace(/^### (.*$)/gm, "<h4>$1</h4>");
    html = html.replace(/^## (.*$)/gm,  "<h3>$1</h3>");
    html = html.replace(/^# (.*$)/gm,   "<h3>$1</h3>");
    // Blockquotes
    html = html.replace(/^&gt; (.*$)/gm, "<blockquote>$1</blockquote>");
    // Unordered lists
    html = html.replace(/^[-*] (.*$)/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*?<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
    // Ordered lists
    html = html.replace(/^\d+\. (.*$)/gm, "<li>$1</li>");
    // Paragraphs
    html = html.replace(/\n\n/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");
    html = "<p>" + html + "</p>";
    // Clean-up
    html = html.replace(/<p><\/p>/g, "");
    html = html.replace(/<p>(<h[34]>)/g, "$1");
    html = html.replace(/(<\/h[34]>)<\/p>/g, "$1");
    html = html.replace(/<p>(<ul>)/g, "$1");
    html = html.replace(/(<\/ul>)<\/p>/g, "$1");
    html = html.replace(/<p>(<pre>)/g, "$1");
    html = html.replace(/(<\/pre>)<\/p>/g, "$1");
    html = html.replace(/<p>(<blockquote>)/g, "$1");
    html = html.replace(/(<\/blockquote>)<\/p>/g, "$1");

    return html;
}

// ============================================================
// Global Error Catchers
// ============================================================
window.addEventListener("unhandledrejection", (e) => {
    const msg = e.reason?.message || String(e.reason) || "An unexpected error occurred.";
    if (msg.includes("Failed to fetch")) {
        showToast("Network error: could not reach the server.", "error");
    } else {
        showToast(msg, "error");
    }
});

// ============================================================
// Expose functions called from inline HTML onclick / onchange
// Guarantees global access even if a bundler/formatter scopes
// the file (e.g., adds "use strict" wrapper or IIFE).
// ============================================================
window.createNewChat        = createNewChat;
window.selectSession        = selectSession;
window.deleteSession        = deleteSession;
window.archiveSession       = archiveSession;
window.toggleDocumentShared = toggleDocumentShared;
window.deleteDocument       = deleteDocument;
window.sendQuery            = sendQuery;
window.deleteChatMemoryEntry = deleteChatMemoryEntry;


