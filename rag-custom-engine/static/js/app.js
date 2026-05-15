/* ═══════════════════════════════════════════════════════════════
   RAG From Scratch — Frontend JavaScript
   ═══════════════════════════════════════════════════════════════ */

// ─────────────────────── State ──────────────────────────
let isQuerying = false;
let currentSessionId = null;
let pipelineVisible = true;
let timelineVisible = false;
let _chartInstances = {}; // track Chart.js instances to destroy on re-render
let _stepData = {};       // step index → full step object, for hover cards
let _hoverTimer = null;   // debounce timer for hover card
let _hoverCard = null;    // current hover card DOM element

// ─────────────────────── Trace Card State ──────────────────────────
let _pendingTraceId = null;
let _pendingSteps = [];
let _pendingTraceStartTime = null;
// Per-trace step counts, keyed by traceId, so older cards keep correct counters
let _traceStepCounts = {};

// ─────────────────────── Init ──────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadConfig();
    setupDragDrop();
    setupFileInput();
    setupKeyboard();
    refreshSessions();
    refreshDocList();
    refreshChatMemory();
});

// ═══════════════════════════════════════════════════════════════
// Pipeline Config
// ═══════════════════════════════════════════════════════════════

function getConfig() {
    return {
        use_multi_query: document.getElementById("cfgMultiQuery").checked,
        use_self_rag: document.getElementById("cfgSelfRAG").checked,
        use_compression: document.getElementById("cfgCompression").checked,
        vector_method: document.getElementById("cfgVectorMethod").value,
        merge_method: document.getElementById("cfgMergeMethod").value,
    };
}

function saveConfig() {
    const cfg = getConfig();
    localStorage.setItem("ragConfig", JSON.stringify(cfg));
    // Update header badges
    document.getElementById("badgeVector").textContent =
        cfg.vector_method === "hnsw" ? "HNSW" : "Brute Force";
    document.getElementById("badgeMerge").textContent =
        cfg.merge_method === "rrf" ? "RRF" : "Weighted";
}

function loadConfig() {
    try {
        const saved = JSON.parse(localStorage.getItem("ragConfig"));
        if (saved) {
            document.getElementById("cfgMultiQuery").checked = !!saved.use_multi_query;
            document.getElementById("cfgSelfRAG").checked = !!saved.use_self_rag;
            document.getElementById("cfgCompression").checked = !!saved.use_compression;
            if (saved.vector_method) document.getElementById("cfgVectorMethod").value = saved.vector_method;
            if (saved.merge_method) document.getElementById("cfgMergeMethod").value = saved.merge_method;
        }
    } catch (e) { /* ignore */ }
    saveConfig(); // Update badges
}

function togglePipeline() {
    const container = document.getElementById("pipelineContainer");
    const text = document.getElementById("pipelineToggleText");
    pipelineVisible = !pipelineVisible;
    container.classList.toggle("collapsed", !pipelineVisible);
    text.textContent = pipelineVisible ? "Hide" : "Show";
}

function toggleTimeline() {
    const timeline = document.getElementById("pipelineTimeline");
    const toggleBtn = document.getElementById("timelineToggleText");
    timelineVisible = !timelineVisible;
    timeline.style.display = timelineVisible ? "block" : "none";
    toggleBtn.textContent = timelineVisible ? "▲ Hide Step Details" : "▼ Show Step Details";
}

function switchPipelineTab(tab) {
    const tracePanel = document.getElementById("pipelineTracePanel");
    const archPanel  = document.getElementById("pipelineArchPanel");
    const tabTrace   = document.getElementById("tabTrace");
    const tabArch    = document.getElementById("tabArch");
    const statusText = document.getElementById("pipelineStatusText");

    if (tab === "trace") {
        tracePanel.style.display = "block";
        archPanel.style.display  = "none";
        tabTrace.classList.add("active");
        tabArch.classList.remove("active");
    } else {
        tracePanel.style.display = "none";
        archPanel.style.display  = "block";
        tabTrace.classList.remove("active");
        tabArch.classList.add("active");
        if (statusText) statusText.textContent = "";
    }
}

// ═══════════════════════════════════════════════════════════════
// Pipeline Visualization
// ═══════════════════════════════════════════════════════════════

const STEP_ICONS = {
    "Query Received": "📝",
    "Self-RAG: Retrieval Decision": "🧠",
    "Multi-Query Expansion": "🔍",
    "Embedding Generation": "🔢",
    "Vector Search": "🧮",
    "BM25 Keyword Search": "📊",
    "Hybrid Merge": "🔀",
    "Self-RAG: Relevance Grading": "✅",
    "Contextual Compression": "🗜️",
    "Cross-Chat Memory Search": "💾",
    "Context Assembly": "📋",
    "LLM Generation": "🤖",
    "Self-RAG: Hallucination Check": "🛡️",
    "Response Ready": "✨",
};

const SHORT_NAMES = {
    "Query Received": "Query",
    "Self-RAG: Retrieval Decision": "Retrieval?",
    "Multi-Query Expansion": "Multi-Q",
    "Embedding Generation": "Embed",
    "Vector Search": "Vector",
    "BM25 Keyword Search": "BM25",
    "Hybrid Merge": "Merge",
    "Self-RAG: Relevance Grading": "Grading",
    "Contextual Compression": "Compress",
    "Cross-Chat Memory Search": "Memory",
    "Context Assembly": "Assembly",
    "LLM Generation": "LLM",
    "Self-RAG: Hallucination Check": "Halluc.",
    "Response Ready": "Done",
};

// ─── Educational explanations for each step ───────────────────
const STEP_EXPLANATIONS = {
    "Query Received": {
        title: "Query Received",
        what: "The user's question is captured along with any prior conversation history.",
        why: "The pipeline needs the raw query text and context to feed into every subsequent step. Chat history enables multi-turn conversations.",
        input: "Raw question text + chat history",
        output: "Validated query + config flags",
    },
    "Self-RAG: Retrieval Decision": {
        title: "Self-RAG: Should we retrieve?",
        what: "An LLM call decides whether document retrieval is necessary for this query.",
        why: "Not every question needs retrieval — greetings, general knowledge, and math don't benefit from document lookup, saving latency and tokens.",
        input: "Question text",
        output: "RETRIEVE or SKIP decision + reasoning",
    },
    "Multi-Query Expansion": {
        title: "Multi-Query Expansion",
        what: "The LLM generates 3 alternative phrasings of the original query.",
        why: "Different wordings capture different relevant chunks. A query about 'ML model accuracy' might miss chunks that discuss 'prediction performance'.",
        input: "Original query",
        output: "3 query variants for broader retrieval",
    },
    "Embedding Generation": {
        title: "Embedding Generation",
        what: "The query is converted into a 1536-dimensional float vector using OpenAI's text-embedding-3-small model.",
        why: "Vectors represent semantic meaning numerically — similar meanings produce vectors that are geometrically close in high-dimensional space.",
        input: "Query text",
        output: "1536-dim semantic vector",
    },
    "Vector Search": {
        title: "Vector Search (Semantic)",
        what: "The query vector is compared against all document chunk vectors using either Brute-Force cosine similarity or the HNSW graph algorithm.",
        why: "Finds semantically similar content even when the exact words don't match — 'automobile insurance' finds chunks about 'car coverage'.",
        input: "Query vector",
        output: "Top-K most similar chunks with similarity scores",
    },
    "BM25 Keyword Search": {
        title: "BM25 Keyword Search (Lexical)",
        what: "Classic Okapi BM25 full-text search using an inverted index with TF-IDF-like scoring.",
        why: "Catches exact keyword matches and noun phrases that vector search misses — crucial for proper nouns, codes, and technical terms.",
        input: "Query text → tokenized",
        output: "Top-K keyword-matched chunks with BM25 scores",
    },
    "Hybrid Merge": {
        title: "Hybrid Merge",
        what: "Vector and BM25 results are merged using either Weighted Ensemble (score normalization + weighted sum) or Reciprocal Rank Fusion (position-based).",
        why: "Neither semantic nor keyword search alone is best. Hybrid approaches consistently outperform single-method retrieval across benchmarks.",
        input: "Vector results + BM25 results",
        output: "Unified ranked list with combined scores",
    },
    "Self-RAG: Relevance Grading": {
        title: "Self-RAG: Relevance Grading",
        what: "An LLM grades each retrieved chunk as relevant or not relevant to the specific question.",
        why: "Retrieval is imperfect — some top-K chunks may not actually answer the question. Filtering noise prevents the LLM from being confused by irrelevant context.",
        input: "Question + retrieved chunks",
        output: "Kept (relevant) and filtered (irrelevant) chunks",
    },
    "Contextual Compression": {
        title: "Contextual Compression",
        what: "An LLM extracts only the sentences from each chunk that are relevant to the query, discarding the rest.",
        why: "Reduces prompt size and focuses the LLM on the signal, not the noise. A 1000-char chunk might have only 150 chars of truly relevant information.",
        input: "Question + retrieved chunks",
        output: "Compressed chunks containing only relevant sentences",
    },
    "Cross-Chat Memory Search": {
        title: "Cross-Chat Memory Search",
        what: "Searches LLM-summarized past conversation archives using vector similarity.",
        why: "Enables the assistant to remember facts from previous sessions — 'as we discussed last week, your project uses FastAPI...'.",
        input: "Query vector",
        output: "Relevant past conversation summaries",
    },
    "Context Assembly": {
        title: "Context Assembly",
        what: "All retrieved chunks and memory summaries are formatted into structured context blocks for the system prompt.",
        why: "The LLM needs context in a clear, labeled format to properly attribute sources and avoid confusion between multiple document chunks.",
        input: "Graded/compressed chunks + memory summaries",
        output: "Formatted context string for LLM prompt",
    },
    "LLM Generation": {
        title: "LLM Generation",
        what: "GPT-4o-mini generates the final answer using the assembled context, chat history, and the system prompt's grounding rules.",
        why: "The LLM synthesizes information from multiple sources, handles multi-turn conversation, and enforces citation and anti-hallucination rules.",
        input: "System prompt + context + history + question",
        output: "Answer text + source citations",
    },
    "Self-RAG: Hallucination Check": {
        title: "Self-RAG: Hallucination Check",
        what: "An LLM verifies whether the generated answer is grounded in the retrieved context.",
        why: "LLMs can 'hallucinate' plausible-sounding but factually incorrect statements. This step flags answers not supported by retrieved evidence.",
        input: "Question + context + generated answer",
        output: "Grounded/Not-Grounded verdict + confidence score",
    },
    "Response Ready": {
        title: "Response Ready",
        what: "The pipeline completes and timing statistics are collected.",
        why: "Provides a performance overview — shows which steps were the bottleneck, what was skipped, and total end-to-end latency.",
        input: "All step results",
        output: "Final answer, sources, timing waterfall",
    },
};

// ─── Initialize the pipeline bar with 14 pending step nodes ───
function initPipelineBar() {
    const bar = document.getElementById("pipelineBar");
    bar.innerHTML = "";
    // Destroy old charts
    Object.values(_chartInstances).forEach(c => { try { c.destroy(); } catch(e){} });
    _chartInstances = {};

    const names = Object.keys(STEP_ICONS);
    names.forEach((name, i) => {
        const node = document.createElement("div");
        node.className = "pipe-node-wrap status-pending";
        node.id = `pipe-node-${i}`;
        const icon = STEP_ICONS[name] || "⚙️";
        const short = SHORT_NAMES[name] || name;
        node.innerHTML = `
            <div class="pipe-node-circle">
                <span class="pipe-node-icon">${icon}</span>
                <span class="pipe-node-spinner" style="display:none">
                    <svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="28" stroke-dashoffset="10" class="spin-circle"/></svg>
                </span>
            </div>
            <div class="pipe-node-label">${escapeHtml(short)}</div>
            <div class="pipe-node-time"></div>
        `;
        // Hover card listeners
        node.addEventListener("mouseenter", () => {
            clearTimeout(_hoverTimer);
            _hoverTimer = setTimeout(() => showStepHoverCard(node, i), 180);
        });
        node.addEventListener("mouseleave", () => {
            clearTimeout(_hoverTimer);
            scheduleHideHoverCard();
        });

        if (i < names.length - 1) {
            const arrow = document.createElement("div");
            arrow.className = "pipe-connector";
            arrow.id = `pipe-conn-${i}`;
            bar.appendChild(node);
            bar.appendChild(arrow);
        } else {
            bar.appendChild(node);
        }
    });

    // Also init the timeline
    const timeline = document.getElementById("pipelineTimeline");
    timeline.innerHTML = "";
    names.forEach((name, i) => {
        const row = document.createElement("div");
        row.className = "tl-row status-pending";
        row.id = `tl-row-${i}`;
        const expl = STEP_EXPLANATIONS[name] || {};
        row.innerHTML = `
            <div class="tl-left">
                <div class="tl-dot"><span>${STEP_ICONS[name] || "⚙️"}</span></div>
                <div class="tl-line" id="tl-line-${i}"></div>
            </div>
            <div class="tl-right">
                <div class="tl-header" onclick="toggleTimelineRow(${i})">
                    <span class="tl-name">${escapeHtml(name)}</span>
                    <div class="tl-header-right">
                        <span class="tl-status-badge" id="tl-badge-${i}">pending</span>
                        <span class="tl-time" id="tl-time-${i}"></span>
                        <button class="tl-info-btn" onclick="showStepExplanation(event, '${escapeHtml(name)}')" title="What does this step do?">?</button>
                        <span class="tl-chevron" id="tl-chev-${i}">▼</span>
                    </div>
                </div>
                <div class="tl-detail" id="tl-detail-${i}" style="display:none">
                    <div class="tl-detail-body" id="tl-detail-body-${i}">
                        <div class="tl-expl-blurb">${escapeHtml(expl.what || "")}</div>
                    </div>
                </div>
            </div>
        `;
        timeline.appendChild(row);
    });

    const toggleEl = document.getElementById("pipelineTimelineToggle");
    toggleEl.style.display = "block";
    if (timelineVisible) {
        document.getElementById("pipelineTimeline").style.display = "block";
    }
}

function toggleTimelineRow(index) {
    const detail = document.getElementById(`tl-detail-${index}`);
    const chev = document.getElementById(`tl-chev-${index}`);
    if (!detail) return;
    const open = detail.style.display !== "none";
    detail.style.display = open ? "none" : "block";
    if (chev) chev.textContent = open ? "▼" : "▲";
}

function showStepExplanation(event, stepName) {
    event.stopPropagation();
    const expl = STEP_EXPLANATIONS[stepName];
    if (!expl) return;

    // Remove existing overlay
    const existing = document.getElementById("stepExplOverlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "stepExplOverlay";
    overlay.className = "step-expl-overlay";
    overlay.innerHTML = `
        <div class="step-expl-card">
            <div class="step-expl-header">
                <span>${STEP_ICONS[stepName] || "⚙️"} ${escapeHtml(expl.title)}</span>
                <button onclick="document.getElementById('stepExplOverlay').remove()">✕</button>
            </div>
            <div class="step-expl-body">
                <div class="step-expl-section">
                    <div class="step-expl-label">What it does</div>
                    <p>${escapeHtml(expl.what)}</p>
                </div>
                <div class="step-expl-section">
                    <div class="step-expl-label">Why it matters</div>
                    <p>${escapeHtml(expl.why)}</p>
                </div>
                <div class="step-expl-io">
                    <div><span class="expl-io-label">Input</span> ${escapeHtml(expl.input || "")}</div>
                    <div><span class="expl-io-label">Output</span> ${escapeHtml(expl.output || "")}</div>
                </div>
            </div>
        </div>
    `;
    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add("visible"));
}

// ─── Called when a step_start event arrives ───────────────────
function onStepStart(index, stepName) {
    const node = document.getElementById(`pipe-node-${index}`);
    if (node) {
        node.className = "pipe-node-wrap status-running";
        const iconEl = node.querySelector(".pipe-node-icon");
        const spinnerEl = node.querySelector(".pipe-node-spinner");
        if (iconEl) iconEl.style.display = "none";
        if (spinnerEl) spinnerEl.style.display = "inline-flex";
    }
    const row = document.getElementById(`tl-row-${index}`);
    if (row) {
        row.className = "tl-row status-running";
        const badge = document.getElementById(`tl-badge-${index}`);
        if (badge) { badge.textContent = "running"; badge.className = "tl-status-badge badge-running"; }
    }
    // Update status text
    const statusText = document.getElementById("pipelineStatusText");
    if (statusText) statusText.textContent = `Running: ${stepName}`;
}

// ─── Called when a step_complete event arrives ─────────────────
function onStepComplete(step, index) {
    const node = document.getElementById(`pipe-node-${index}`);
    if (node) {
        node.className = `pipe-node-wrap status-${step.status}`;
        const iconEl = node.querySelector(".pipe-node-icon");
        const spinnerEl = node.querySelector(".pipe-node-spinner");
        if (iconEl) iconEl.style.display = "inline";
        if (spinnerEl) spinnerEl.style.display = "none";

        // Status icon override
        if (step.status === "completed") {
            iconEl.textContent = STEP_ICONS[step.name] || "⚙️";
        } else if (step.status === "skipped") {
            iconEl.textContent = "⏭";
        } else if (step.status === "error") {
            iconEl.textContent = "❌";
        }

        // Timing chip
        const timeEl = node.querySelector(".pipe-node-time");
        if (step.duration_ms > 0) {
            timeEl.textContent = step.duration_ms < 1000
                ? `${Math.round(step.duration_ms)}ms`
                : `${(step.duration_ms / 1000).toFixed(1)}s`;
            timeEl.className = "pipe-node-time " + getTimingClass(step.duration_ms);
        } else if (step.status === "skipped") {
            timeEl.textContent = "skip";
            timeEl.className = "pipe-node-time skip";
        }
    }

    // Activate connector
    const conn = document.getElementById(`pipe-conn-${index}`);
    if (conn) {
        conn.classList.add(`conn-${step.status}`);
    }

    // Save step data for hover cards
    _stepData[index] = step;

    // Update timeline row
    const row = document.getElementById(`tl-row-${index}`);
    if (row) {
        row.className = `tl-row status-${step.status}`;
        const badge = document.getElementById(`tl-badge-${index}`);
        if (badge) {
            badge.textContent = step.status;
            badge.className = `tl-status-badge badge-${step.status}`;
        }
        const timeEl = document.getElementById(`tl-time-${index}`);
        if (timeEl && step.duration_ms > 0) {
            timeEl.textContent = step.duration_ms < 1000
                ? `${Math.round(step.duration_ms)}ms`
                : `${(step.duration_ms / 1000).toFixed(1)}s`;
        }
        // Render detail
        const detailBody = document.getElementById(`tl-detail-body-${index}`);
        if (detailBody) {
            detailBody.innerHTML = buildRichStepDetail(step, `chart-${index}`);
            // Render charts after DOM insertion
            requestAnimationFrame(() => renderStepCharts(step, `chart-${index}`));
        }
        // Draw the connecting line
        const line = document.getElementById(`tl-line-${index}`);
        if (line) line.classList.add(`line-${step.status}`);
    }
}

function getTimingClass(ms) {
    if (ms < 100) return "fast";
    if (ms < 500) return "medium";
    return "slow";
}

// ─── Rich detail renderer for timeline rows ──────────────────
function buildRichStepDetail(step, chartId) {
    const d = step.details || {};
    const expl = STEP_EXPLANATIONS[step.name] || {};
    let html = `<div class="tl-expl-blurb">${escapeHtml(expl.what || "")}</div>`;

    if (step.input_summary) {
        html += `<div class="tl-detail-row"><span class="tl-detail-key">Input</span><span class="tl-detail-val">${escapeHtml(step.input_summary)}</span></div>`;
    }
    if (step.output_summary) {
        html += `<div class="tl-detail-row"><span class="tl-detail-key">Output</span><span class="tl-detail-val">${escapeHtml(step.output_summary)}</span></div>`;
    }

    // ── Per-step rich rendering ──────────────────────────────
    if (step.name === "Query Received") {
        if (d.query) html += `<div class="detail-query-box">${escapeHtml(d.query)}</div>`;
        html += _tagRow("Config Active", (d.config_flags || []).map(f =>
            `<span class="detail-tag tag-blue">${escapeHtml(f)}</span>`).join(""));
        if (d.history_turns > 0) {
            html += _textRow("Chat History", `${d.history_turns} prior turns`);
        }
    }

    else if (step.name === "Self-RAG: Retrieval Decision") {
        const grn = d.decision === "RETRIEVE";
        html += `<div class="detail-decision-badge ${grn ? "badge-retrieve" : "badge-skip"}">${escapeHtml(d.decision || "—")}</div>`;
        if (d.reasoning) html += `<div class="detail-reasoning">${escapeHtml(d.reasoning)}</div>`;
    }

    else if (step.name === "Multi-Query Expansion") {
        if (d.original_query) html += _textRow("Original", d.original_query);
        if (d.variants && d.variants.length > 0) {
            const cards = d.variants.map((v, i) =>
                `<div class="detail-variant-card"><span class="detail-variant-num">#${i+1}</span>${escapeHtml(v)}</div>`
            ).join("");
            html += `<div class="detail-variants">${cards}</div>`;
        }
    }

    else if (step.name === "Embedding Generation") {
        html += _textRow("Model", d.model || "text-embedding-3-small");
        html += _textRow("Dimensions", d.dimensions || 1536);
        if (d.vector_preview && d.vector_preview.length > 0) {
            html += `<div class="detail-label">Vector preview (first 64 dims)</div>`;
            html += buildVectorHeatmap(d.vector_preview, chartId + "-heatmap");
            html += `<div class="detail-vec-range">min: ${d.vector_min} &nbsp;|&nbsp; max: ${d.vector_max}</div>`;
        }
    }

    else if (step.name === "Vector Search") {
        html += _textRow("Method", (d.method || "brute_force").toUpperCase());
        html += _textRow("K", d.k || 5);
        html += _textRow("Time", `${d.time_ms || 0}ms`);
        if (d.results && d.results.length > 0) {
            html += `<div class="detail-label">Top results</div>`;
            html += `<canvas id="${chartId}-scores" class="detail-chart" height="120"></canvas>`;
            html += buildResultCards(d.results, "score");
        }
    }

    else if (step.name === "BM25 Keyword Search") {
        html += _textRow("Time", `${d.time_ms || 0}ms`);
        if (d.matched_terms && Object.keys(d.matched_terms).length > 0) {
            const terms = Object.entries(d.matched_terms).slice(0, 8);
            const chips = terms.map(([t, f]) =>
                `<span class="detail-term-chip">${escapeHtml(t)} <span class="term-freq">${f}</span></span>`
            ).join("");
            html += `<div class="detail-label">Matched terms (doc freq)</div><div class="detail-terms">${chips}</div>`;
        }
        if (d.results && d.results.length > 0) {
            html += `<div class="detail-label">Top results</div>`;
            html += `<canvas id="${chartId}-scores" class="detail-chart" height="120"></canvas>`;
            html += buildResultCards(d.results, "score");
        }
    }

    else if (step.name === "Hybrid Merge") {
        html += _textRow("Method", (d.merge_type || d.method || "weighted").toUpperCase());
        if (d.vector_weight !== undefined) {
            html += _textRow("Weights", `Vector ${(d.vector_weight * 100).toFixed(0)}% / BM25 ${(d.bm25_weight * 100).toFixed(0)}%`);
        }
        if (d.scores && d.scores.length > 0) {
            html += `<div class="detail-label">Score breakdown</div>`;
            html += buildScoreTable(d.scores);
        }
    }

    else if (step.name === "Self-RAG: Relevance Grading") {
        if (d.kept !== undefined) {
            html += `<div class="detail-grade-summary">
                <span class="grade-kept">✓ ${d.kept} kept</span>
                <span class="grade-filtered">✗ ${d.filtered} filtered</span>
            </div>`;
        }
        if (d.decisions && d.decisions.length > 0) {
            html += `<div class="detail-label">Grading decisions</div>`;
            d.decisions.forEach(dec => {
                const cls = dec.relevant ? "grade-row-kept" : "grade-row-filtered";
                const icon = dec.relevant ? "✓" : "✗";
                html += `<div class="grade-row ${cls}">
                    <span class="grade-icon">${icon}</span>
                    <div>
                        <div class="grade-snippet">${escapeHtml(dec.snippet)}</div>
                        <div class="grade-reason">${escapeHtml(dec.reason)}</div>
                    </div>
                </div>`;
            });
        }
    }

    else if (step.name === "Contextual Compression") {
        if (d.ratio !== undefined) {
            const pct = Math.round(d.ratio * 100);
            html += `<div class="detail-compress-ratio">
                <span class="compress-label">Compression</span>
                <div class="compress-bar-wrap"><div class="compress-bar" style="width:${pct}%;--w:${pct}%"></div></div>
                <span class="compress-pct">${pct}%</span>
            </div>`;
            html += _textRow("Original", `${d.original_chars} chars`);
            html += _textRow("Compressed", `${d.compressed_chars} chars`);
        }
        if (d.items && d.items.length > 0) {
            html += `<canvas id="${chartId}-compress" class="detail-chart" height="100"></canvas>`;
        }
    }

    else if (step.name === "Cross-Chat Memory Search") {
        if (d.memories && d.memories.length > 0) {
            d.memories.forEach(m => {
                html += `<div class="detail-memory-card">
                    <div class="memory-card-title">🧠 ${escapeHtml(m.session_title)}</div>
                    <div class="memory-card-meta">${escapeHtml(m.archived_at)} · ${m.message_count} msgs</div>
                    <div class="memory-card-snippet">${escapeHtml(m.snippet)}</div>
                </div>`;
            });
        } else {
            html += `<div class="detail-empty">No relevant past conversations found</div>`;
        }
    }

    else if (step.name === "Context Assembly") {
        html += _textRow("Document chunks", d.doc_chunks || 0);
        html += _textRow("Memory chunks", d.memory_chunks || 0);
        html += _textRow("Total chars", d.total_chars || 0);
        html += _textRow("History msgs", d.history_messages || 0);
        if (d.context_preview) {
            html += `<div class="detail-label">Context preview</div>`;
            html += `<div class="detail-context-preview">${escapeHtml(d.context_preview)}${d.total_chars > 300 ? "..." : ""}</div>`;
        }
    }

    else if (step.name === "LLM Generation") {
        html += _textRow("Model", d.model || "");
        html += _textRow("Temperature", d.temperature || 0.1);
        html += _textRow("Total tokens", d.total_tokens || 0);
        if (d.prompt_tokens !== undefined && d.completion_tokens !== undefined) {
            html += `<div class="detail-label">Token usage</div>`;
            html += `<canvas id="${chartId}-tokens" class="detail-chart-sm" height="120" width="120"></canvas>`;
            html += `<div class="detail-token-legend">
                <span class="token-dot dot-prompt"></span> Prompt: ${d.prompt_tokens}
                <span class="token-dot dot-completion" style="margin-left:12px"></span> Completion: ${d.completion_tokens}
            </div>`;
        }
        if (d.answer_preview) {
            html += `<div class="detail-label">Answer preview</div>`;
            html += `<div class="detail-answer-preview">${escapeHtml(d.answer_preview)}${(d.answer_length || 0) > 150 ? "..." : ""}</div>`;
        }
    }

    else if (step.name === "Self-RAG: Hallucination Check") {
        if (d.grounded !== undefined) {
            const cls = d.grounded ? "grounded-yes" : "grounded-no";
            const label = d.grounded ? "✓ GROUNDED" : "⚠ NOT GROUNDED";
            html += `<div class="detail-grounded-badge ${cls}">${label}</div>`;
            const confPct = Math.round((d.confidence || 0) * 100);
            html += `<div class="detail-label">Confidence</div>`;
            html += `<div class="detail-confidence-bar-wrap">
                <div class="detail-confidence-bar ${cls}" style="width:${confPct}%;--w:${confPct}%"></div>
                <span class="detail-confidence-pct">${confPct}%</span>
            </div>`;
            if (d.reasoning) html += `<div class="detail-reasoning">${escapeHtml(d.reasoning)}</div>`;
            if (d.action) {
                html += `<div class="detail-warning">⚠ ${escapeHtml(d.action)}</div>`;
            }
        }
    }

    else if (step.name === "Response Ready") {
        html += _textRow("Total time", `${d.total_time_ms || 0}ms`);
        html += _textRow("Steps completed", d.steps_completed || 0);
        html += _textRow("Steps skipped", d.steps_skipped || 0);
        html += _textRow("Steps errored", d.steps_errored || 0);
        if (d.waterfall && d.waterfall.length > 0) {
            html += `<div class="detail-label">Timing waterfall</div>`;
            html += `<canvas id="${chartId}-waterfall" class="detail-chart" height="160"></canvas>`;
        }
    }

    else if (step.status === "error") {
        html += `<div class="detail-error-msg">${escapeHtml(step.output_summary)}</div>`;
    }

    return html;
}

// ═══════════════════════════════════════════════════════════════
// Hover Cards — pipeline bar node hover
// ═══════════════════════════════════════════════════════════════

function showStepHoverCard(nodeEl, index) {
    const step = _stepData[index];
    if (!step) return; // step not yet completed — no data to show

    hideStepHoverCard();

    const card = document.createElement("div");
    card.className = "step-hover-card";
    card.id = "stepHoverCard";
    card.innerHTML = buildHoverCardContent(step);

    // Keep card visible when mouse moves into it
    card.addEventListener("mouseenter", () => clearTimeout(_hoverTimer));
    card.addEventListener("mouseleave", () => scheduleHideHoverCard());

    document.body.appendChild(card);
    _hoverCard = card;

    // Position: centre above the node, flip below if near top edge
    const rect = nodeEl.getBoundingClientRect();
    const cardW = 320;
    card.style.width = cardW + "px";

    // Temporarily show to measure height
    card.style.visibility = "hidden";
    card.style.display = "block";
    const cardH = card.offsetHeight;
    card.style.visibility = "";

    const spaceAbove = rect.top - 8;
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    let top, arrowClass;

    if (spaceAbove >= cardH || spaceAbove >= spaceBelow) {
        top = rect.top - cardH - 10;
        arrowClass = "arrow-bottom";
    } else {
        top = rect.bottom + 10;
        arrowClass = "arrow-top";
    }

    let left = rect.left + rect.width / 2 - cardW / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - cardW - 8));

    card.style.top  = `${top + window.scrollY}px`;
    card.style.left = `${left}px`;
    card.classList.add(arrowClass);

    // Animate in
    requestAnimationFrame(() => card.classList.add("visible"));
}

function scheduleHideHoverCard() {
    _hoverTimer = setTimeout(hideStepHoverCard, 120);
}

function hideStepHoverCard() {
    if (_hoverCard) {
        _hoverCard.remove();
        _hoverCard = null;
    }
}

function buildHoverCardContent(step) {
    const d      = step.details || {};
    const icon   = STEP_ICONS[step.name] || "⚙️";
    const expl   = STEP_EXPLANATIONS[step.name] || {};
    const dur    = step.duration_ms > 0
        ? (step.duration_ms < 1000 ? `${Math.round(step.duration_ms)}ms` : `${(step.duration_ms/1000).toFixed(1)}s`)
        : (step.status === "skipped" ? "skipped" : "—");

    const statusLabel = {
        completed: '<span class="hc-badge hc-badge-completed">✓ done</span>',
        skipped:   '<span class="hc-badge hc-badge-skipped">⏭ skipped</span>',
        error:     '<span class="hc-badge hc-badge-error">✗ error</span>',
        running:   '<span class="hc-badge hc-badge-running">● running</span>',
    }[step.status] || "";

    let body = "";

    // ── per-step detail sections ──────────────────────────────
    if (step.name === "Query Received") {
        if (d.query) body += hcBlock("Query", escapeHtml(d.query));
        if (d.config_flags) body += hcTags("Active", d.config_flags);
        if (d.history_turns > 0) body += hcRow("History", `${d.history_turns} prior turns`);
    }

    else if (step.name === "Self-RAG: Retrieval Decision") {
        const yes = d.decision === "RETRIEVE";
        body += `<div class="hc-decision ${yes ? "hc-retrieve" : "hc-skip"}">${escapeHtml(d.decision || "—")}</div>`;
        if (d.reasoning) body += hcBlock("Reasoning", escapeHtml(d.reasoning));
    }

    else if (step.name === "Multi-Query Expansion") {
        if (d.original_query) body += hcRow("Original", escapeHtml(d.original_query));
        if (d.variants && d.variants.length) {
            body += "<div class='hc-label'>Variants</div>";
            d.variants.forEach((v, i) =>
                body += `<div class="hc-variant"><span class="hc-vnum">#${i+1}</span>${escapeHtml(v)}</div>`
            );
        }
    }

    else if (step.name === "Embedding Generation") {
        body += hcRow("Model", d.model || "text-embedding-3-small");
        body += hcRow("Dimensions", d.dimensions || 1536);
        if (d.vector_min !== undefined) body += hcRow("Value range", `${d.vector_min} → ${d.vector_max}`);
        if (d.vector_preview) {
            body += "<div class='hc-label'>Vector preview (64 dims)</div>";
            body += buildMiniHeatmap(d.vector_preview);
        }
    }

    else if (step.name === "Vector Search") {
        body += hcRow("Method", (d.method || "brute_force").toUpperCase());
        if (d.time_ms !== undefined) body += hcRow("Search time", `${d.time_ms}ms`);
        if (d.results && d.results.length) {
            body += "<div class='hc-label'>Top results</div>";
            body += buildMiniResultBars(d.results, "score", "rgba(59,130,246,0.7)");
        }
    }

    else if (step.name === "BM25 Keyword Search") {
        if (d.time_ms !== undefined) body += hcRow("Search time", `${d.time_ms}ms`);
        if (d.matched_terms && Object.keys(d.matched_terms).length) {
            const chips = Object.entries(d.matched_terms).slice(0, 6)
                .map(([t, f]) => `<span class="hc-chip">${escapeHtml(t)} <em>${f}</em></span>`).join("");
            body += `<div class="hc-label">Matched terms</div><div class="hc-chips">${chips}</div>`;
        }
        if (d.results && d.results.length) {
            body += "<div class='hc-label'>Top results</div>";
            body += buildMiniResultBars(d.results, "score", "rgba(245,158,11,0.7)");
        }
    }

    else if (step.name === "Hybrid Merge") {
        body += hcRow("Method", (d.merge_type || d.method || "weighted").toUpperCase());
        if (d.vector_weight !== undefined)
            body += hcRow("Weights", `Vector ${(d.vector_weight*100).toFixed(0)}% / BM25 ${(d.bm25_weight*100).toFixed(0)}%`);
        if (d.scores && d.scores.length) {
            body += "<div class='hc-label'>Combined scores</div>";
            d.scores.slice(0, 4).forEach(s => {
                const pct = Math.round((s.combined_score || 0) * 100);
                body += `<div class="hc-score-row">
                    <span class="hc-score-name">${escapeHtml(truncate(s.filename || "?", 22))}</span>
                    <div class="hc-bar-wrap"><div class="hc-bar-fill" style="width:${pct}%;background:rgba(16,185,129,0.7)"></div></div>
                    <span class="hc-score-val">${(s.combined_score||0).toFixed(3)}</span>
                </div>`;
            });
        }
    }

    else if (step.name === "Self-RAG: Relevance Grading") {
        if (d.kept !== undefined) {
            body += `<div class="hc-grade-summary">
                <span class="hc-kept">✓ ${d.kept} kept</span>
                <span class="hc-filtered">✗ ${d.filtered} filtered</span>
            </div>`;
        }
        (d.decisions || []).slice(0, 3).forEach(dec => {
            body += `<div class="hc-grade-row ${dec.relevant ? "hc-grade-kept" : "hc-grade-filtered"}">
                <span>${dec.relevant ? "✓" : "✗"}</span>
                <span>${escapeHtml(dec.snippet || "")}</span>
            </div>`;
        });
    }

    else if (step.name === "Contextual Compression") {
        if (d.ratio !== undefined) {
            const pct = Math.round(d.ratio * 100);
            body += hcRow("Ratio", `${pct}% retained`);
            body += `<div class="hc-compress-bar-wrap">
                <div class="hc-compress-bar" style="width:${pct}%"></div>
            </div>`;
            body += hcRow("Before → After", `${d.original_chars} → ${d.compressed_chars} chars`);
        }
    }

    else if (step.name === "Cross-Chat Memory Search") {
        if (!d.memories || !d.memories.length) {
            body += `<div class="hc-empty">No relevant past conversations</div>`;
        } else {
            d.memories.slice(0, 3).forEach(m =>
                body += `<div class="hc-memory-item">
                    <div class="hc-mem-title">🧠 ${escapeHtml(m.session_title)}</div>
                    <div class="hc-mem-snippet">${escapeHtml(truncate(m.snippet || "", 80))}</div>
                </div>`
            );
        }
    }

    else if (step.name === "Context Assembly") {
        body += hcRow("Doc chunks", d.doc_chunks || 0);
        body += hcRow("Memory chunks", d.memory_chunks || 0);
        body += hcRow("Total chars", d.total_chars || 0);
        body += hcRow("History messages", d.history_messages || 0);
        if (d.context_preview)
            body += hcBlock("Preview", escapeHtml(truncate(d.context_preview, 160)));
    }

    else if (step.name === "LLM Generation") {
        body += hcRow("Model", d.model || "gpt-4o-mini");
        body += hcRow("Temperature", d.temperature || 0.1);
        if (d.total_tokens)
            body += hcRow("Tokens", `${d.prompt_tokens} prompt + ${d.completion_tokens} completion = ${d.total_tokens}`);
        if (d.answer_preview)
            body += hcBlock("Answer preview", escapeHtml(truncate(d.answer_preview, 160)));
    }

    else if (step.name === "Self-RAG: Hallucination Check") {
        if (d.grounded !== undefined) {
            body += `<div class="hc-grounded ${d.grounded ? "hc-grounded-yes" : "hc-grounded-no"}">${d.grounded ? "✓ GROUNDED" : "⚠ NOT GROUNDED"}</div>`;
            const pct = Math.round((d.confidence || 0) * 100);
            body += `<div class="hc-conf-bar-wrap"><div class="hc-conf-bar ${d.grounded ? "hc-conf-yes" : "hc-conf-no"}" style="width:${pct}%"></div></div>`;
            body += hcRow("Confidence", `${pct}%`);
            if (d.reasoning) body += hcBlock("Reasoning", escapeHtml(truncate(d.reasoning, 140)));
        }
    }

    else if (step.name === "Response Ready") {
        body += hcRow("Total time", `${d.total_time_ms || 0}ms`);
        body += hcRow("Completed", d.steps_completed || 0);
        body += hcRow("Skipped", d.steps_skipped || 0);
        if (d.waterfall && d.waterfall.length) {
            body += "<div class='hc-label'>Timing</div>";
            const max = Math.max(...d.waterfall.map(w => w.duration_ms || 0), 1);
            d.waterfall.filter(w => w.duration_ms > 0).slice(0, 6).forEach(w => {
                const pct = Math.round((w.duration_ms / max) * 100);
                const col = w.status === "completed" ? "rgba(16,185,129,0.7)"
                          : w.status === "skipped" ? "rgba(245,158,11,0.5)"
                          : "rgba(239,68,68,0.7)";
                body += `<div class="hc-score-row">
                    <span class="hc-score-name">${escapeHtml(truncate(SHORT_NAMES[w.name] || w.name, 10))}</span>
                    <div class="hc-bar-wrap"><div class="hc-bar-fill" style="width:${pct}%;background:${col}"></div></div>
                    <span class="hc-score-val">${w.duration_ms}ms</span>
                </div>`;
            });
        }
    }

    // Input/output summaries as fallback
    if (!body && step.input_summary)  body += hcRow("Input", escapeHtml(step.input_summary));
    if (!body && step.output_summary) body += hcRow("Output", escapeHtml(step.output_summary));

    return `
        <div class="hc-header">
            <span class="hc-icon">${icon}</span>
            <span class="hc-name">${escapeHtml(step.name)}</span>
            ${statusLabel}
            <span class="hc-dur">${escapeHtml(dur)}</span>
        </div>
        ${expl.what ? `<div class="hc-what">${escapeHtml(expl.what)}</div>` : ""}
        <div class="hc-body">${body}</div>
        <div class="hc-footer">Click step in timeline for full detail</div>
    `;
}

// ─── Mini inline bar chart (no canvas) ───────────────────────
function buildMiniResultBars(results, scoreKey, color) {
    const max = Math.max(...results.map(r => r[scoreKey] || 0), 0.001);
    return results.slice(0, 4).map(r => {
        const pct = Math.round(((r[scoreKey] || 0) / max) * 100);
        return `<div class="hc-score-row">
            <span class="hc-score-name">${escapeHtml(truncate(r.filename || "?", 22))}</span>
            <div class="hc-bar-wrap"><div class="hc-bar-fill" style="width:${pct}%;background:${color}"></div></div>
            <span class="hc-score-val">${(r[scoreKey]||0).toFixed(3)}</span>
        </div>`;
    }).join("");
}

// ─── Mini 8×8 heatmap (CSS-only, compact) ────────────────────
function buildMiniHeatmap(values) {
    const slice = values.slice(0, 64);
    const max = Math.max(...slice.map(Math.abs), 0.001);
    let html = `<div class="hc-heatmap">`;
    for (let i = 0; i < 64; i++) {
        const v = slice[i] || 0;
        const norm = v / max;
        let r, g, b;
        if (norm >= 0) { r = Math.round(239*norm); g = Math.round(68*norm); b = Math.round(68*norm); }
        else { const n=-norm; r = Math.round(59*n); g = Math.round(130*n); b = Math.round(246*n); }
        html += `<div class="hc-hcell" style="background:rgb(${r},${g},${b})" title="[${i}]: ${v.toFixed(4)}"></div>`;
    }
    return html + "</div>";
}

// ─── Small helpers for hover card rows ────────────────────────
function hcRow(k, v) {
    return `<div class="hc-row"><span class="hc-key">${escapeHtml(k)}</span><span class="hc-val">${v}</span></div>`;
}
function hcBlock(k, v) {
    return `<div class="hc-label">${escapeHtml(k)}</div><div class="hc-block">${v}</div>`;
}
function hcTags(k, arr) {
    const chips = arr.map(t => `<span class="hc-chip">${escapeHtml(t)}</span>`).join("");
    return `<div class="hc-row"><span class="hc-key">${escapeHtml(k)}</span><span class="hc-val hc-val-chips">${chips}</span></div>`;
}

// ─── Chart renderer (called after DOM insertion) ─────────────
function renderStepCharts(step, chartId) {
    const d = step.details || {};

    if (step.name === "Vector Search" || step.name === "BM25 Keyword Search") {
        const results = d.results || [];
        if (results.length === 0) return;
        const canvas = document.getElementById(`${chartId}-scores`);
        if (!canvas) return;
        const labels = results.map(r => truncate(r.filename || "?", 15));
        const scores = results.map(r => r.score || 0);
        destroyChart(`${chartId}-scores`);
        _chartInstances[`${chartId}-scores`] = new Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Score",
                    data: scores,
                    backgroundColor: step.name === "Vector Search"
                        ? "rgba(59,130,246,0.7)" : "rgba(245,158,11,0.7)",
                    borderRadius: 4,
                }],
            },
            options: {
                indexAxis: "y",
                responsive: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, max: 1, ticks: { font: { size: 10 } } },
                    y: { ticks: { font: { size: 10 } } },
                },
                animation: { duration: 600, easing: "easeOutQuart" },
            },
        });
    }

    else if (step.name === "LLM Generation" && d.prompt_tokens !== undefined) {
        const canvas = document.getElementById(`${chartId}-tokens`);
        if (!canvas) return;
        destroyChart(`${chartId}-tokens`);
        _chartInstances[`${chartId}-tokens`] = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: ["Prompt", "Completion"],
                datasets: [{
                    data: [d.prompt_tokens, d.completion_tokens],
                    backgroundColor: ["rgba(99,102,241,0.8)", "rgba(16,185,129,0.8)"],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: false,
                cutout: "60%",
                plugins: { legend: { display: false } },
                animation: { duration: 600 },
            },
        });
    }

    else if (step.name === "Contextual Compression" && d.items && d.items.length > 0) {
        const canvas = document.getElementById(`${chartId}-compress`);
        if (!canvas) return;
        destroyChart(`${chartId}-compress`);
        const labels = d.items.map((_, i) => `Chunk ${i+1}`);
        _chartInstances[`${chartId}-compress`] = new Chart(canvas, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label: "Original", data: d.items.map(it => it.original_len || 0), backgroundColor: "rgba(148,163,184,0.6)", borderRadius: 3 },
                    { label: "Compressed", data: d.items.map(it => it.compressed_len || 0), backgroundColor: "rgba(34,197,94,0.7)", borderRadius: 3 },
                ],
            },
            options: {
                responsive: false,
                plugins: { legend: { position: "top", labels: { font: { size: 10 }, boxWidth: 10 } } },
                scales: {
                    x: { ticks: { font: { size: 9 } } },
                    y: { beginAtZero: true, ticks: { font: { size: 9 } } },
                },
                animation: { duration: 600 },
            },
        });
    }

    else if (step.name === "Response Ready" && d.waterfall && d.waterfall.length > 0) {
        const canvas = document.getElementById(`${chartId}-waterfall`);
        if (!canvas) return;
        destroyChart(`${chartId}-waterfall`);
        const filtered = d.waterfall.filter(w => w.duration_ms > 0);
        const colors = filtered.map(w =>
            w.status === "completed" ? "rgba(16,185,129,0.75)" :
            w.status === "skipped"   ? "rgba(245,158,11,0.55)" :
                                       "rgba(239,68,68,0.75)"
        );
        _chartInstances[`${chartId}-waterfall`] = new Chart(canvas, {
            type: "bar",
            data: {
                labels: filtered.map(w => truncate(SHORT_NAMES[w.name] || w.name, 10)),
                datasets: [{
                    label: "Duration (ms)",
                    data: filtered.map(w => w.duration_ms),
                    backgroundColor: colors,
                    borderRadius: 3,
                }],
            },
            options: {
                responsive: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { font: { size: 9 } } },
                    y: { beginAtZero: true, ticks: { font: { size: 9 } } },
                },
                animation: { duration: 700 },
            },
        });
    }
}

function destroyChart(id) {
    if (_chartInstances[id]) {
        try { _chartInstances[id].destroy(); } catch(e){}
        delete _chartInstances[id];
    }
}

// ─── Vector heatmap (8×8 CSS grid) ────────────────────────────
function buildVectorHeatmap(values, id) {
    const slice = values.slice(0, 64);
    const max = Math.max(...slice.map(Math.abs), 0.001);
    let html = `<div class="vec-heatmap" id="${id}">`;
    for (let i = 0; i < 64; i++) {
        const v = (slice[i] || 0);
        const norm = v / max; // -1..1
        let r, g, b;
        if (norm >= 0) {
            r = Math.round(239 * norm); g = Math.round(68 * norm); b = Math.round(68 * norm);
        } else {
            const n = -norm;
            r = Math.round(59 * n); g = Math.round(130 * n); b = Math.round(246 * n);
        }
        html += `<div class="vec-cell" style="background:rgb(${r},${g},${b})" title="dim[${i}]: ${v.toFixed(4)}"></div>`;
    }
    html += `</div>`;
    return html;
}

// ─── Hybrid score table ────────────────────────────────────────
function buildScoreTable(scores) {
    const hasVec = scores.some(s => s.vector_score !== undefined);
    let html = `<table class="detail-score-table">
        <thead><tr>
            <th>Document</th>
            ${hasVec ? `<th>Vector</th><th>BM25</th>` : ""}
            <th>Combined</th>
        </tr></thead><tbody>`;
    scores.forEach(s => {
        const combined = s.combined_score || 0;
        html += `<tr>
            <td class="score-filename">${escapeHtml(truncate(s.filename || "?", 20))}</td>
            ${hasVec ? `
                <td><div class="score-bar-cell"><div class="score-bar-fill" style="width:${(s.vector_score||0)*100}%;background:rgba(59,130,246,0.6)"></div><span>${(s.vector_score||0).toFixed(3)}</span></div></td>
                <td><div class="score-bar-cell"><div class="score-bar-fill" style="width:${(s.bm25_score||0)*100}%;background:rgba(245,158,11,0.6)"></div><span>${(s.bm25_score||0).toFixed(3)}</span></div></td>
            ` : ""}
            <td><div class="score-bar-cell"><div class="score-bar-fill" style="width:${combined*100}%;background:rgba(16,185,129,0.7)"></div><span>${combined.toFixed(3)}</span></div></td>
        </tr>`;
    });
    html += `</tbody></table>`;
    return html;
}

// ─── Result cards for vector/BM25 hits ────────────────────────
function buildResultCards(results, scoreKey) {
    return results.slice(0, 3).map(r => `
        <div class="detail-result-card">
            <div class="result-card-top">
                <span class="result-filename">${escapeHtml(truncate(r.filename || "", 20))}</span>
                <span class="result-score">${(r[scoreKey] || 0).toFixed(3)}</span>
            </div>
            <div class="result-snippet">${escapeHtml(r.snippet || "")}</div>
        </div>
    `).join("");
}

// ─── Utility helpers ──────────────────────────────────────────
function _textRow(key, val) {
    return `<div class="tl-detail-row"><span class="tl-detail-key">${escapeHtml(key)}</span><span class="tl-detail-val">${escapeHtml(String(val))}</span></div>`;
}
function _tagRow(key, tagsHtml) {
    return `<div class="tl-detail-row"><span class="tl-detail-key">${escapeHtml(key)}</span><span class="tl-detail-val tags-val">${tagsHtml}</span></div>`;
}
function truncate(str, n) {
    return str && str.length > n ? str.slice(0, n) + "…" : str;
}

// ─── Legacy renderPipelineSteps (kept for non-streaming fallback) ───
function renderPipelineSteps(steps) {
    initPipelineBar();
    steps.forEach((step, i) => onStepComplete(step, i));
}

// ═══════════════════════════════════════════════════════════════
// Inline Pipeline Trace Card
// ═══════════════════════════════════════════════════════════════

function appendTraceCard(traceId) {
    _pendingSteps = [];
    _pendingTraceStartTime = performance.now();
    _traceStepCounts[traceId] = 0;
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message trace-message";
    div.id = `trace-${traceId}`;
    div.innerHTML = `
        <div class="trace-card processing" id="trace-card-${traceId}">
            <button class="trace-toggle-btn" onclick="toggleInlineTrace('${traceId}')">
                <span class="material-icons-round trace-toggle-icon">sync</span>
                <span class="trace-toggle-label" id="trace-label-${traceId}">Pipeline running\u2026</span>
                <span class="trace-step-counter" id="trace-counter-${traceId}">0</span>
                <span class="material-icons-round trace-chevron" id="trace-chev-${traceId}" style="display:none">expand_more</span>
            </button>
            <div class="trace-step-list" id="trace-steps-${traceId}" style="display:block"></div>
        </div>
    `;
    chatArea.appendChild(div);
    scrollToBottom();
}

function updateTraceCard(traceId, step) {
    if (!traceId) return;
    _pendingSteps.push(step);
    // Track per-trace step count so the counter is always correct for this card
    _traceStepCounts[traceId] = (_traceStepCounts[traceId] || 0) + 1;
    const list = document.getElementById(`trace-steps-${traceId}`);
    if (!list) return;

    const iconMap = { completed: "check_circle", skipped: "do_not_disturb_on", error: "error", running: "pending" };
    const icon = iconMap[step.status] || "radio_button_unchecked";
    const dur = step.duration_ms > 0
        ? (step.duration_ms < 1000 ? `${Math.round(step.duration_ms)}ms` : `${(step.duration_ms / 1000).toFixed(1)}s`)
        : (step.status === "skipped" ? "skip" : "");

    const row = document.createElement("div");
    row.className = `trace-step-row trace-${step.status}`;
    row.innerHTML = `
        <span class="material-icons-round trace-step-icon">${icon}</span>
        <span class="trace-step-name">${escapeHtml(step.name)}</span>
        ${dur ? `<span class="trace-step-dur">${dur}</span>` : ""}
    `;
    list.appendChild(row);
    scrollToBottom();

    const counter = document.getElementById(`trace-counter-${traceId}`);
    if (counter) counter.textContent = _traceStepCounts[traceId];
}

function finalizeTraceCard(traceId) {
    if (!traceId) return;
    const totalMs = Math.round(performance.now() - (_pendingTraceStartTime || 0));
    const card    = document.getElementById(`trace-card-${traceId}`);
    const label   = document.getElementById(`trace-label-${traceId}`);
    const counter = document.getElementById(`trace-counter-${traceId}`);
    const icon    = card ? card.querySelector(".trace-toggle-icon") : null;
    const chev    = document.getElementById(`trace-chev-${traceId}`);
    const list    = document.getElementById(`trace-steps-${traceId}`);

    const stepCount = _traceStepCounts[traceId] || _pendingSteps.length;

    if (card)    card.classList.remove("processing");
    if (label)   label.textContent = "Pipeline trace";
    if (counter) {
        const dur = totalMs < 1000 ? `${totalMs}ms` : `${(totalMs / 1000).toFixed(1)}s`;
        counter.textContent = `${stepCount} steps \u00b7 ${dur}`;
    }
    if (icon)    icon.textContent = "account_tree";
    if (chev)    chev.style.display = "inline";
    // Collapse the step list now that the trace is complete; user can re-open
    if (list)    list.style.display = "none";
    if (card)    card.classList.remove("expanded");
    if (chev)    chev.textContent = "expand_more";
    _pendingTraceId = null;
}

function toggleInlineTrace(traceId) {
    const card = document.getElementById(`trace-card-${traceId}`);
    const list = document.getElementById(`trace-steps-${traceId}`);
    const chev = document.getElementById(`trace-chev-${traceId}`);
    if (!list || !card) return;
    const open = list.style.display !== "none";
    list.style.display = open ? "none" : "block";
    if (chev)  chev.textContent = open ? "expand_more" : "expand_less";
    if (card)  card.classList.toggle("expanded", !open);
}

// ═══════════════════════════════════════════════════════════════
// Query — SSE Streaming
// ═══════════════════════════════════════════════════════════════

async function sendQuery() {
    const ta = document.getElementById("queryInput");
    const question = ta.value.trim();
    if (!question || isQuerying) return;

    isQuerying = true;
    document.getElementById("sendBtn").disabled = true;
    ta.value = "";
    ta.style.height = "auto";

    // Hide welcome message
    const welcome = document.getElementById("welcomeMessage");
    if (welcome) welcome.style.display = "none";

    appendUserMessage(question);

    // Create inline pipeline trace card
    const traceId = Date.now().toString(36);
    _pendingTraceId = traceId;
    appendTraceCard(traceId);

    showLoading(true);

    // Initialize pipeline bar with 14 pending nodes
    initPipelineBar();
    // Switch to trace tab and make pipeline visible
    switchPipelineTab("trace");
    if (!pipelineVisible) togglePipeline();
    document.getElementById("pipelineStatusText").textContent = "Starting…";

    const config = getConfig();
    const body = {
        question,
        session_id: currentSessionId,
        pipeline_config: config,
    };

    // Build a map: step_name → index
    const stepNames = Object.keys(STEP_ICONS);
    const stepIndex = {};
    stepNames.forEach((name, i) => { stepIndex[name] = i; });

    let currentStepIdx = -1;
    let buffer = "";
    let gotAnswer = false;

    try {
        const res = await fetch("/api/query/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || `HTTP ${res.status}`, "error");
            showLoading(false);
            isQuerying = false;
            document.getElementById("sendBtn").disabled = false;
            document.getElementById("pipelineStatusText").textContent = "";
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process all complete SSE events in the buffer
            let boundary;
            while ((boundary = buffer.indexOf("\n\n")) !== -1) {
                const raw = buffer.slice(0, boundary).trim();
                buffer = buffer.slice(boundary + 2);

                if (!raw.startsWith("data: ")) continue;
                let event;
                try {
                    event = JSON.parse(raw.slice(6));
                } catch (e) { continue; }

                if (event.type === "step_start") {
                    const idx = stepIndex[event.step_name];
                    if (idx !== undefined) {
                        currentStepIdx = idx;
                        onStepStart(idx, event.step_name);
                    }
                } else if (event.type === "step_complete") {
                    const idx = stepIndex[event.step.name];
                    if (idx !== undefined) {
                        onStepComplete(event.step, idx);
                    }
                    // Update inline trace card
                    updateTraceCard(_pendingTraceId, event.step);
                } else if (event.type === "answer") {
                    gotAnswer = true;
                    const data = event.data;
                    if (data.session_id && !currentSessionId) {
                        currentSessionId = data.session_id;
                    }
                    // Finalize trace card before the answer message
                    finalizeTraceCard(_pendingTraceId);
                    showLoading(false);
                    appendAssistantMessage(data.answer, data.sources || [], data.cross_chat_refs || []);
                    document.getElementById("pipelineStatusText").textContent = "Complete";
                    // Auto-rename session on first message
                    _autoRenameSession(question);
                    refreshSessions();
                    updateBadges();
                } else if (event.type === "error") {
                    showToast(event.data.message || "Pipeline error", "error");
                    showLoading(false);
                    document.getElementById("pipelineStatusText").textContent = "Error";
                }
            }
        }
    } catch (err) {
        showToast(err.message || "Network error", "error");
        document.getElementById("pipelineStatusText").textContent = "Error";
    } finally {
        if (!gotAnswer) showLoading(false);
        isQuerying = false;
        document.getElementById("sendBtn").disabled = false;
    }
}

// ═══════════════════════════════════════════════════════════════
// Messages
// ═══════════════════════════════════════════════════════════════

function appendUserMessage(text) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message user-message";
    div.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatArea.appendChild(div);
    scrollToBottom();
}

function appendAssistantMessage(answer, sources, crossChatRefs) {
    const chatArea = document.getElementById("chatArea");
    const div = document.createElement("div");
    div.className = "message assistant-message";

    // Sources HTML
    let sourcesHtml = "";
    if (sources && sources.length > 0) {
        const cards = sources.map(s => `
            <div class="source-card">
                <span class="source-filename">${escapeHtml(s.filename)}</span>
                <span class="source-meta">Page: ${s.page} · Chunk: ${s.chunk_index}</span>
                <p class="source-snippet">${escapeHtml(s.snippet)}</p>
            </div>
        `).join("");
        sourcesHtml = `
            <div class="sources-section">
                <details class="sources-toggle">
                    <summary><span class="material-icons-round" style="font-size:13px;vertical-align:middle">source</span> ${sources.length} source${sources.length > 1 ? "s" : ""} retrieved</summary>
                    <div class="source-cards">${cards}</div>
                </details>
            </div>
        `;
    }

    // Cross-chat refs HTML
    let refsHtml = "";
    if (crossChatRefs && crossChatRefs.length > 0) {
        const refCards = crossChatRefs.map(r => `
            <div class="cross-chat-ref-card">
                <div class="ref-session-title"><span class="material-icons-round" style="font-size:13px;vertical-align:middle">psychology</span> ${escapeHtml(r.session_title)}</div>
                <div class="ref-session-meta">${escapeHtml(r.archived_at)}</div>
                <p class="ref-snippet">${escapeHtml(r.snippet)}</p>
            </div>
        `).join("");
        refsHtml = `
            <div class="cross-chat-section">
                <details class="sources-toggle">
                    <summary><span class="material-icons-round" style="font-size:13px;vertical-align:middle">psychology</span> ${crossChatRefs.length} past conversation${crossChatRefs.length > 1 ? "s" : ""}</summary>
                    <div class="source-cards">${refCards}</div>
                </details>
            </div>
        `;
    }

    div.innerHTML = `
        <div class="assistant-card">
            <div class="assistant-answer">${renderMarkdown(answer)}</div>
            ${sourcesHtml}
            ${refsHtml}
        </div>
    `;
    chatArea.appendChild(div);
    scrollToBottom();
}

function showLoading(show) {
    document.getElementById("loadingIndicator").style.display = show ? "flex" : "none";
}

function scrollToBottom() {
    const chatArea = document.getElementById("chatArea");
    chatArea.scrollTop = chatArea.scrollHeight;
}

// ═══════════════════════════════════════════════════════════════
// Sessions
// ═══════════════════════════════════════════════════════════════

async function createNewChat() {
    try {
        const res = await fetch("/api/sessions", { method: "POST" });
        if (!res.ok) return;
        const session = await res.json();
        currentSessionId = session.id;
        await refreshSessions();
        clearChatArea();
    } catch (e) {
        showToast("Failed to create session", "error");
    }
}

async function selectSession(sessionId) {
    currentSessionId = sessionId;
    highlightActiveSession();
    clearChatArea();

    try {
        // Fetch messages and traces in parallel
        const [sessionRes, tracesRes] = await Promise.all([
            fetch(`/api/sessions/${sessionId}`),
            fetch(`/api/sessions/${sessionId}/traces`),
        ]);

        // Guard: user may have switched to a different session while fetching
        if (currentSessionId !== sessionId) return;
        if (!sessionRes.ok) return;

        const data      = await sessionRes.json();

        // Guard again after the second await
        if (currentSessionId !== sessionId) return;

        const traceData = tracesRes.ok ? await tracesRes.json() : { traces: [] };

        // Final guard before touching the DOM
        if (currentSessionId !== sessionId) return;

        const traces    = traceData.traces || [];

        if (data.messages && data.messages.length > 0) {
            const welcome = document.getElementById("welcomeMessage");
            if (welcome) welcome.style.display = "none";

            document.getElementById("inChatCount").textContent = data.messages.length;

            // Walk messages in user/assistant pairs; insert saved trace for every turn
            let turnIndex = 0;
            let i = 0;
            let lastTraceId = null;
            while (i < data.messages.length) {
                const msg = data.messages[i];
                if (msg.role === "user") {
                    appendUserMessage(msg.content);
                    const trace = traces[turnIndex];
                    if (trace) {
                        appendSavedTraceCard(trace);
                        lastTraceId = trace.trace_id;
                    }
                    if (i + 1 < data.messages.length && data.messages[i + 1].role === "assistant") {
                        appendAssistantMessage(data.messages[i + 1].content, [], []);
                        i += 2;
                    } else {
                        i += 1;
                    }
                    turnIndex++;
                } else {
                    // Orphaned assistant message (no preceding user message)
                    appendAssistantMessage(msg.content, [], []);
                    i++;
                }
            }

            // Auto-expand the most recent trace card so the user sees the last run's steps
            if (lastTraceId) {
                const list = document.getElementById(`trace-steps-${lastTraceId}`);
                const chev = document.getElementById(`trace-chev-${lastTraceId}`);
                const card = document.getElementById(`trace-card-${lastTraceId}`);
                if (list) list.style.display = "block";
                if (chev) chev.textContent = "expand_less";
                if (card) card.classList.add("expanded");
            }
        }
        updateBadges();
    } catch (e) {
        showToast("Failed to load session", "error");
    }
}

function appendSavedTraceCard(trace) {
    const traceId  = trace.trace_id;
    const totalMs  = trace.total_duration_ms;
    const steps    = trace.steps || [];
    const chatArea = document.getElementById("chatArea");
    const div      = document.createElement("div");
    div.className  = "message trace-message";
    div.id         = `trace-${traceId}`;

    const iconMap = { completed: "check_circle", skipped: "do_not_disturb_on", error: "error" };
    const stepRows = steps.map(step => {
        const icon = iconMap[step.status] || "pending";
        const dur  = step.duration_ms > 0
            ? (step.duration_ms < 1000
                ? `${Math.round(step.duration_ms)}ms`
                : `${(step.duration_ms / 1000).toFixed(1)}s`)
            : (step.status === "skipped" ? "skip" : "");
        return `<div class="trace-step-row trace-${step.status}">
            <span class="material-icons-round trace-step-icon">${icon}</span>
            <span class="trace-step-name">${escapeHtml(step.name)}</span>
            ${dur ? `<span class="trace-step-dur">${dur}</span>` : ""}
        </div>`;
    }).join("");

    const totalStr = totalMs < 1000 ? `${Math.round(totalMs)}ms` : `${(totalMs / 1000).toFixed(1)}s`;
    div.innerHTML = `
        <div class="trace-card" id="trace-card-${traceId}">
            <button class="trace-toggle-btn" onclick="toggleInlineTrace('${traceId}')">
                <span class="material-icons-round trace-toggle-icon">account_tree</span>
                <span class="trace-toggle-label" id="trace-label-${traceId}">Pipeline trace</span>
                <span class="trace-step-counter" id="trace-counter-${traceId}">${steps.length} steps \u00b7 ${totalStr}</span>
                <span class="material-icons-round trace-chevron" id="trace-chev-${traceId}">expand_more</span>
            </button>
            <div class="trace-step-list" id="trace-steps-${traceId}" style="display:none">
                ${stepRows}
            </div>
        </div>`;
    chatArea.appendChild(div);
    scrollToBottom();
}

async function deleteSession(sessionId, e) {
    e.stopPropagation();
    try {
        const res = await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
        if (res.ok) {
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                clearChatArea();
            }
            await refreshSessions();
            await refreshChatMemory();
            showToast("Session deleted & archived", "success");
        }
    } catch (e) {
        showToast("Failed to delete session", "error");
    }
}

async function archiveSession(sessionId, e) {
    e.stopPropagation();
    try {
        const res = await fetch(`/api/sessions/${sessionId}/archive`, { method: "POST" });
        if (res.ok) {
            await refreshChatMemory();
            showToast("Session archived to memory", "success");
        } else {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Archive failed", "error");
        }
    } catch (e) {
        showToast("Archive failed", "error");
    }
}

async function refreshSessions() {
    try {
        const res = await fetch("/api/sessions");
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById("sessionList");
        list.innerHTML = "";

        if (data.sessions.length === 0) {
            list.innerHTML = '<div style="font-size:12px;color:rgba(255,255,255,0.3);padding:8px">No chats yet</div>';
            return;
        }

        for (const s of data.sessions) {
            const active = s.id === currentSessionId ? " active" : "";
            const div = document.createElement("div");
            div.className = `session-item${active}`;
            div.onclick = () => selectSession(s.id);
            div.innerHTML = `
                <span class="session-title">${escapeHtml(s.title)}</span>
                <span class="session-meta">${s.message_count}msg</span>
                <div class="session-actions">
                    <button title="Archive" onclick="archiveSession('${s.id}', event)"><span class="material-icons-round" style="font-size:15px">archive</span></button>
                    <button title="Delete" onclick="deleteSession('${s.id}', event)"><span class="material-icons-round" style="font-size:15px">delete</span></button>
                </div>
            `;
            list.appendChild(div);
        }

        // Auto-select first session if none selected
        if (!currentSessionId && data.sessions.length > 0) {
            selectSession(data.sessions[0].id);
        }
    } catch (e) { /* ignore */ }
}

function highlightActiveSession() {
    document.querySelectorAll(".session-item").forEach(el => {
        el.classList.remove("active");
    });
    // Re-highlight will happen on next refreshSessions
}

function clearChatArea() {
    const chatArea = document.getElementById("chatArea");
    chatArea.innerHTML = `
        <div class="welcome-message" id="welcomeMessage">
            <div class="welcome-icon"><span class="material-icons-round" style="font-size:52px;color:var(--accent)">auto_awesome</span></div>
            <h2>RAG From Scratch</h2>
            <p>Every component built from the ground up — no LangChain, no ChromaDB.</p>
            <div class="feature-cards">
                <div class="feature-card"><span class="material-icons-round feature-card-icon">scatter_plot</span><h4>Vector Search</h4><p>Brute-force cosine &amp; HNSW</p></div>
                <div class="feature-card"><span class="material-icons-round feature-card-icon">manage_search</span><h4>BM25</h4><p>Okapi BM25 from scratch</p></div>
                <div class="feature-card"><span class="material-icons-round feature-card-icon">merge_type</span><h4>Hybrid</h4><p>Weighted &amp; RRF merge</p></div>
                <div class="feature-card"><span class="material-icons-round feature-card-icon">smart_toy</span><h4>Self-RAG</h4><p>Adaptive retrieval</p></div>
                <div class="feature-card"><span class="material-icons-round feature-card-icon">search</span><h4>Multi-Query</h4><p>Query variants</p></div>
                <div class="feature-card"><span class="material-icons-round feature-card-icon">compress</span><h4>Compression</h4><p>Context compression</p></div>
            </div>
        </div>
    `;
    // Reset pipeline
    const bar = document.getElementById("pipelineBar");
    if (bar) bar.innerHTML = '<div class="pipeline-bar-empty">Ask a question to see the pipeline in action</div>';
    const timeline = document.getElementById("pipelineTimeline");
    if (timeline) timeline.innerHTML = "";
    const toggleEl = document.getElementById("pipelineTimelineToggle");
    if (toggleEl) toggleEl.style.display = "none";
    const statusText = document.getElementById("pipelineStatusText");
    if (statusText) statusText.textContent = "";
    Object.values(_chartInstances).forEach(c => { try { c.destroy(); } catch(e){} });
    _chartInstances = {};
    _stepData = {};
    _traceStepCounts = {};
    _pendingTraceId = null;
    _pendingSteps = [];
    hideStepHoverCard();
}

// ═══════════════════════════════════════════════════════════════
// Documents
// ═══════════════════════════════════════════════════════════════

function setupDragDrop() {
    const zone = document.getElementById("uploadZone");
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");
        for (const file of e.dataTransfer.files) uploadFile(file);
    });
}

function setupFileInput() {
    document.getElementById("fileInput").addEventListener("change", (e) => {
        for (const file of e.target.files) uploadFile(file);
        e.target.value = "";
    });
}

async function uploadFile(file) {
    showUploadProgress(`Uploading ${file.name}...`);

    const form = new FormData();
    form.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: form });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Upload failed", "error");
            hideUploadProgress();
            return;
        }
        const data = await res.json();
        showUploadProgress(`✓ ${data.num_chunks} chunks from ${data.filename}`, true);
        showToast(data.message, "success");
        setTimeout(hideUploadProgress, 2000);
        await refreshDocList();
        updateBadges();
    } catch (e) {
        showToast(e.message || "Upload failed", "error");
        hideUploadProgress();
    }
}

function showUploadProgress(msg, complete = false) {
    const el = document.getElementById("uploadProgress");
    const text = document.getElementById("progressText");
    const fill = document.getElementById("progressFill");
    el.classList.add("active");
    text.textContent = msg;
    fill.style.width = complete ? "100%" : "60%";
}

function hideUploadProgress() {
    const el = document.getElementById("uploadProgress");
    el.classList.remove("active");
    document.getElementById("progressFill").style.width = "0%";
}

async function refreshDocList() {
    try {
        const res = await fetch("/api/documents");
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById("docList");
        list.innerHTML = "";

        if (data.documents.length === 0) {
            list.innerHTML = '<div style="font-size:12px;color:rgba(255,255,255,0.3);padding:8px">No documents uploaded</div>';
            return;
        }

        for (const doc of data.documents) {
            const div = document.createElement("div");
            div.className = "doc-item";
            div.innerHTML = `
                <span class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                <span class="doc-chunks">${doc.chunk_count} chunks</span>
                <div class="doc-actions">
                    <label class="toggle-switch" title="Share across chats">
                        <input type="checkbox" ${doc.is_shared ? "checked" : ""}
                               onchange="toggleDocShared('${escapeHtml(doc.filename)}', this.checked)" />
                        <span class="toggle-track"></span>
                    </label>
                    <button class="doc-delete" onclick="deleteDocument('${escapeHtml(doc.filename)}')" title="Delete"><span class="material-icons-round" style="font-size:14px">delete</span></button>
                </div>
            `;
            list.appendChild(div);
        }

        // Update shared count
        const sharedCount = data.documents.filter(d => d.is_shared).length;
        document.getElementById("sharedDocCount").textContent = sharedCount;
    } catch (e) { /* ignore */ }
}

async function deleteDocument(filename) {
    try {
        const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
        if (res.ok) {
            showToast(`Deleted ${filename}`, "success");
            await refreshDocList();
        } else {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "Delete failed", "error");
        }
    } catch (e) {
        showToast("Delete failed", "error");
    }
}

async function toggleDocShared(filename, shared) {
    try {
        await fetch(`/api/documents/${encodeURIComponent(filename)}/shared`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ shared }),
        });
        await refreshDocList();
    } catch (e) { /* ignore */ }
}

// ═══════════════════════════════════════════════════════════════
// Inter-Chat Memory
// ═══════════════════════════════════════════════════════════════

async function refreshChatMemory() {
    try {
        const res = await fetch("/api/chat-memory");
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById("memoryList");
        list.innerHTML = "";

        document.getElementById("interChatCount").textContent = data.total;

        if (data.entries.length === 0) {
            list.innerHTML = '<div style="font-size:12px;color:rgba(255,255,255,0.3);padding:8px">No archived memories</div>';
            return;
        }

        for (const entry of data.entries) {
            const div = document.createElement("div");
            div.className = "memory-item";
            div.innerHTML = `
                <div class="memory-title">
                    <span>${escapeHtml(entry.session_title)}</span>
                    <button class="memory-delete" onclick="deleteChatMemory('${entry.session_id}')" title="Delete">✕</button>
                </div>
                <div class="memory-summary">${escapeHtml(entry.summary)}</div>
            `;
            list.appendChild(div);
        }
    } catch (e) { /* ignore */ }
}

async function deleteChatMemory(sessionId) {
    try {
        const res = await fetch(`/api/chat-memory/${sessionId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Memory deleted", "success");
            await refreshChatMemory();
        }
    } catch (e) {
        showToast("Failed to delete memory", "error");
    }
}

// ═══════════════════════════════════════════════════════════════
// Badges
// ═══════════════════════════════════════════════════════════════

async function updateBadges() {
    // In-chat count
    if (currentSessionId) {
        try {
            const res = await fetch(`/api/sessions/${currentSessionId}`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById("inChatCount").textContent = data.messages.length;
            }
        } catch (e) { /* ignore */ }
    }
}

// Auto-rename session from the first message text
async function _autoRenameSession(question) {
    if (!currentSessionId || !question) return;
    try {
        // Only rename if session title is still the default
        const sRes = await fetch(`/api/sessions`);
        if (!sRes.ok) return;
        const sData = await sRes.json();
        const session = sData.sessions.find(s => s.id === currentSessionId);
        if (!session || (session.title !== "New Chat" && session.title !== "")) return;
        const title = question.trim().slice(0, 50);
        await fetch(`/api/sessions/${currentSessionId}/rename`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title }),
        });
    } catch (e) { /* ignore */ }
}

// ═══════════════════════════════════════════════════════════════
// Keyboard
// ═══════════════════════════════════════════════════════════════

function setupKeyboard() {
    const ta = document.getElementById("queryInput");
    ta.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    });
    ta.addEventListener("input", () => {
        ta.style.height = "auto";
        ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    });
}

// ═══════════════════════════════════════════════════════════════
// Markdown Renderer (basic, no external lib)
// ═══════════════════════════════════════════════════════════════

function renderMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);

    // Fenced code blocks: ```lang\ncode\n```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic: *text*
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Headers
    html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

    // Blockquotes: > text
    html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");

    // Unordered lists
    html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

    // Paragraphs
    html = html.replace(/\n\n/g, "</p><p>");
    html = "<p>" + html + "</p>";

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, "");
    html = html.replace(/<p>(<h[1-3]>)/g, "$1");
    html = html.replace(/(<\/h[1-3]>)<\/p>/g, "$1");
    html = html.replace(/<p>(<pre>)/g, "$1");
    html = html.replace(/(<\/pre>)<\/p>/g, "$1");
    html = html.replace(/<p>(<ul>)/g, "$1");
    html = html.replace(/(<\/ul>)<\/p>/g, "$1");
    html = html.replace(/<p>(<blockquote>)/g, "$1");
    html = html.replace(/(<\/blockquote>)<\/p>/g, "$1");

    return html;
}

// ═══════════════════════════════════════════════════════════════
// Toast Notifications
// ═══════════════════════════════════════════════════════════════

const TOAST_ICONS = {
    error: "❌",
    success: "✅",
    warning: "⚠️",
    info: "ℹ️",
};
const TOAST_TITLES = { error: "Error", success: "Success", warning: "Warning", info: "Info" };
const TOAST_DURATIONS = { error: 7000, success: 4000, warning: 5000, info: 5000 };

function showToast(msg, type = "error") {
    const container = document.getElementById("toastContainer");
    const duration = TOAST_DURATIONS[type] || 5000;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${TOAST_ICONS[type]}</div>
        <div class="toast-body">
            <div class="toast-title">${TOAST_TITLES[type]}</div>
            <div class="toast-msg">${escapeHtml(msg)}</div>
        </div>
        <button class="toast-close" onclick="dismissToast(this.parentElement)">&times;</button>
        <div class="toast-progress">
            <div class="toast-bar" style="animation-duration:${duration}ms"></div>
        </div>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() =>
        requestAnimationFrame(() => toast.classList.add("toast-show"))
    );
    setTimeout(() => dismissToast(toast), duration);
}

function dismissToast(toast) {
    if (!toast || !toast.parentElement) return;
    toast.classList.remove("toast-show");
    toast.classList.add("toast-hide");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
}

// ═══════════════════════════════════════════════════════════════
// Utility
// ═══════════════════════════════════════════════════════════════

function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
