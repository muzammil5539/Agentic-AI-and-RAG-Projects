"""
capture_screenshots.py
Starts the rag-custom-engine server, waits for it to be ready, then uses
Playwright (headless Chromium) to capture 8 raw screenshots of the UI.

Run from the rag-custom-engine/ directory:
    python scripts/capture_screenshots.py
"""

import os
import sys
import time
import json
import subprocess
import socket
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR   = Path(__file__).resolve().parent.parent
SS_DIR     = BASE_DIR / "screenshots"
SERVER_URL = "http://localhost:8001"
VIEWPORT   = {"width": 1440, "height": 900}

SS_DIR.mkdir(exist_ok=True)


# ── Server helpers ────────────────────────────────────────────────────

def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def start_server() -> subprocess.Popen | None:
    if _port_open("localhost", 8001):
        print("[server] Already running on :8001")
        return None
    print("[server] Starting server …")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        time.sleep(1)
        if _port_open("localhost", 8001):
            print("[server] Ready on :8001")
            return proc
    proc.terminate()
    raise RuntimeError("Server did not start within 30 s")


def stop_server(proc: subprocess.Popen | None):
    if proc:
        proc.terminate()
        proc.wait(timeout=5)
        print("[server] Stopped")


# ── JS helpers injected into page ────────────────────────────────────

MOCK_PIPELINE_STEPS_JS = """
(function() {
    // Build mock pipeline step bars similar to real trace
    const steps = [
        {name:"Cross-Session Memory", status:"completed", duration_ms:38,  output_summary:"Found 0 relevant past sessions"},
        {name:"Retrieval Decision",   status:"completed", duration_ms:412, output_summary:"Retrieval needed"},
        {name:"Multi-Query Expand",   status:"completed", duration_ms:731, output_summary:"3 query variants generated"},
        {name:"Embed Query",          status:"completed", duration_ms:189, output_summary:"1536-dim vector"},
        {name:"Hybrid Search",        status:"completed", duration_ms:24,  output_summary:"10 candidates retrieved"},
        {name:"Relevance Grading",    status:"completed", duration_ms:891, output_summary:"7/10 chunks passed"},
        {name:"Compression",          status:"completed", duration_ms:1240,output_summary:"Avg 61% compression"},
        {name:"Answer Generation",    status:"completed", duration_ms:2108,output_summary:"Answer generated (312 tokens)"},
        {name:"Hallucination Check",  status:"completed", duration_ms:543, output_summary:"Grounded (confidence: 0.95)"},
    ];
    const bar = document.getElementById('pipelineBar');
    if (!bar) return;
    bar.innerHTML = '';
    steps.forEach(s => {
        const el = document.createElement('div');
        el.className = 'pipeline-step completed';
        el.innerHTML = `<span class="step-name">${s.name}</span><span class="step-badge">${s.duration_ms} ms</span>`;
        el.style.cssText = 'display:flex;align-items:center;justify-content:space-between;background:#1e4620;border:1px solid #4ade80;border-radius:6px;padding:6px 12px;margin:3px 0;font-size:12px;color:#d1fae5;';
        const badge = el.querySelector('.step-badge');
        if (badge) badge.style.cssText = 'background:#166534;color:#86efac;border-radius:4px;padding:1px 6px;font-size:11px;';
        bar.appendChild(el);
    });
    const statusText = document.getElementById('pipelineStatusText');
    if (statusText) { statusText.textContent = 'Completed in 6.2 s'; statusText.style.color='#4ade80'; }
    document.getElementById('pipelineTimelineToggle').style.display = 'block';
    const timeline = document.getElementById('pipelineTimeline');
    if (timeline) {
        timeline.style.display = 'block';
        timeline.innerHTML = steps.map(s => `
            <div style="border-left:2px solid #4ade80;padding:8px 14px;margin:4px 0;">
                <div style="font-weight:600;color:#d1fae5;font-size:13px;">${s.name}</div>
                <div style="color:#6b7280;font-size:11px;">Output: ${s.output_summary}</div>
                <div style="color:#4ade80;font-size:11px;">${s.duration_ms} ms</div>
            </div>`).join('');
    }
})();
"""

MOCK_CHAT_ANSWER_JS = """
(function() {
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.style.display = 'none';
    const area = document.getElementById('chatArea');
    if (!area) return;
    area.innerHTML = `
    <div style="padding:16px;max-width:800px;margin:0 auto;">
        <div style="margin-bottom:20px;">
            <div style="background:#1e293b;border-radius:12px 12px 4px 12px;padding:12px 16px;margin-bottom:8px;color:#e2e8f0;font-size:14px;max-width:70%;margin-left:auto;text-align:right;">
                What is Reciprocal Rank Fusion and how does it work?
            </div>
        </div>
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:4px 12px 12px 12px;padding:16px;color:#e2e8f0;font-size:14px;line-height:1.7;">
            <p><strong>Reciprocal Rank Fusion (RRF)</strong> is a rank aggregation technique that combines multiple ranked result lists into a single unified ranking. It was introduced by Cormack, Clarke, and Buettcher (2009) as a robust method for combining results from different retrieval systems.</p>
            <p>The scoring formula for each document <em>d</em> is:</p>
            <div style="background:#1e293b;border-radius:6px;padding:10px;font-family:monospace;font-size:13px;margin:8px 0;">
                RRF_score(d) = Σ 1 / (k + rank_i(d))
            </div>
            <p>where <code style="background:#1e293b;padding:1px 5px;border-radius:3px;">k</code> is a constant (typically 60) and <code style="background:#1e293b;padding:1px 5px;border-radius:3px;">rank_i(d)</code> is the rank of document <em>d</em> in result list <em>i</em>.</p>
            <p><strong>Key advantage:</strong> RRF is robust to score scale differences between retrievers. A document appearing in both vector search and BM25 results receives a compounded score, regardless of the raw scores each retriever assigned. <span style="color:#94a3b8;font-size:12px;">[Source: rag_paper.pdf, Chunk: 7]</span></p>
            <hr style="border-color:#1e293b;margin:12px 0;"/>
            <div style="font-size:12px;color:#64748b;">
                <strong style="color:#94a3b8;">References</strong><br/>
                • rag_paper.pdf · Page 3 · Chunk 7: "RRF combines rankings from multiple retrieval systems using a position-based formula…"<br/>
                • hnsw_overview.pdf · Page 1 · Chunk 2: "Approximate nearest neighbour search methods like HNSW are commonly used in hybrid retrieval…"
            </div>
        </div>
    </div>`;

    // Update memory badges
    const inChat = document.getElementById('inChatCount');
    if (inChat) inChat.textContent = '2';
})();
"""

MOCK_MEMORY_JS = """
(function() {
    const list = document.getElementById('memoryList');
    if (!list) return;
    const entries = [
        { title: 'HNSW Algorithm Discussion', date: '2026-05-17', msgs: 8  },
        { title: 'BM25 vs TF-IDF Comparison', date: '2026-05-16', msgs: 12 },
        { title: 'RAG Pipeline Optimisation',  date: '2026-05-15', msgs: 6  },
    ];
    list.innerHTML = entries.map(e => `
        <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px 10px;margin:4px 0;cursor:pointer;">
            <div style="color:#e2e8f0;font-size:12px;font-weight:600;">${e.title}</div>
            <div style="color:#64748b;font-size:11px;">${e.date} · ${e.msgs} messages</div>
        </div>`).join('');
    const badge = document.getElementById('interChatCount');
    if (badge) badge.textContent = entries.length;
})();
"""

MOCK_DOC_UPLOAD_JS = """
(function() {
    const list = document.getElementById('docList');
    if (!list) return;
    const docs = [
        { name: 'rag_comprehensive_paper.pdf', chunks: 47, shared: true  },
        { name: 'hnsw_overview.pdf',           chunks: 23, shared: false },
        { name: 'bm25_scoring_guide.txt',      chunks: 11, shared: false },
    ];
    list.innerHTML = docs.map(d => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;border-radius:6px;background:#1e293b;margin:3px 0;font-size:12px;">
            <div style="flex:1;min-width:0;">
                <div style="color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${d.name}</div>
                <div style="color:#64748b;font-size:11px;">${d.chunks} chunks</div>
            </div>
            <div style="width:20px;height:20px;border-radius:50%;background:${d.shared ? '#166534' : '#334155'};display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;margin-left:6px;">
                <span style="color:${d.shared ? '#4ade80' : '#64748b'};font-size:10px;">${d.shared ? '✓' : '·'}</span>
            </div>
        </div>`).join('');
    const sharedBadge = document.getElementById('sharedDocCount');
    if (sharedBadge) sharedBadge.textContent = '1';
})();
"""


# ── Screenshot capture tasks ──────────────────────────────────────────

async def capture_all():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx     = await browser.new_context(viewport=VIEWPORT)
        page    = await ctx.new_page()

        print("[1/8] App Overview …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SS_DIR / "raw_01_app_overview.png"), full_page=False)

        print("[2/8] Pipeline Config bar …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(800)
        # Scroll to the config bar and grab a taller crop in annotate step
        await page.evaluate("document.getElementById('pipelineConfig').scrollIntoView({behavior:'instant',block:'center'})")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(SS_DIR / "raw_02_pipeline_config.png"), full_page=False)

        print("[3/8] Document Upload (mock docs) …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.evaluate(MOCK_DOC_UPLOAD_JS)
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SS_DIR / "raw_03_document_upload.png"), full_page=False)

        print("[4/8] Pipeline Trace (mock steps) …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.evaluate(MOCK_PIPELINE_STEPS_JS)
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SS_DIR / "raw_04_pipeline_trace.png"), full_page=False)

        print("[5/8] Pipeline Trace expanded details …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.evaluate(MOCK_PIPELINE_STEPS_JS)
        await page.evaluate("""
            const tl = document.getElementById('pipelineTimeline');
            if (tl) tl.style.display = 'block';
            const toggleBtn = document.getElementById('pipelineTimelineToggle');
            if (toggleBtn) toggleBtn.style.display = 'block';
        """)
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SS_DIR / "raw_05_pipeline_trace_details.png"), full_page=False)

        print("[6/8] System Architecture tab …")
        # Use a taller viewport to show all 4 phases of the architecture diagram
        await ctx.set_viewport_size({"width": 1440, "height": 1800})
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(800)
        await page.click("#tabArch")
        await page.wait_for_timeout(600)
        await page.evaluate("""
            const body = document.getElementById('pipelineBody');
            if (body) { body.style.maxHeight = 'none'; body.style.overflow = 'visible'; }
            const chat = document.querySelector('.chat-area');
            if (chat) chat.style.display = 'none';
            const qbar = document.querySelector('.query-bar');
            if (qbar) qbar.style.display = 'none';
            const cfg = document.getElementById('pipelineConfig');
            if (cfg) cfg.style.display = 'none';
        """)
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(SS_DIR / "raw_06_system_architecture.png"), full_page=True)
        # Reset viewport
        await ctx.set_viewport_size(VIEWPORT)

        print("[7/8] RAG Answer with citations …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        # Collapse the pipeline panel so the chat area is visible
        await page.evaluate("""
            const body = document.getElementById('pipelineBody');
            if (body) body.style.display = 'none';
            const toggleText = document.getElementById('pipelineToggleText');
            if (toggleText) toggleText.textContent = 'Show';
        """)
        await page.evaluate(MOCK_PIPELINE_STEPS_JS)
        await page.evaluate(MOCK_CHAT_ANSWER_JS)
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(SS_DIR / "raw_07_rag_answer.png"), full_page=False)

        print("[8/8] Cross-session memory panel …")
        await page.goto(SERVER_URL, wait_until="networkidle", timeout=15000)
        # Collapse pipeline to give memory panel more visual prominence
        await page.evaluate("""
            const body = document.getElementById('pipelineBody');
            if (body) body.style.display = 'none';
        """)
        await page.evaluate(MOCK_MEMORY_JS)
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(SS_DIR / "raw_08_cross_session_memory.png"), full_page=False)

        await browser.close()

    print(f"\n✅  8 raw screenshots saved to {SS_DIR}")


if __name__ == "__main__":
    server_proc = None
    try:
        server_proc = start_server()
        asyncio.run(capture_all())
    finally:
        stop_server(server_proc)
