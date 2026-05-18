"""
annotate_screenshots.py
Takes the 8 raw_*.png screenshots and adds numbered callout boxes,
highlight overlays, and labels using Pillow.

Run from the rag-custom-engine/ directory:
    python scripts/annotate_screenshots.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SS_DIR = Path(__file__).resolve().parent.parent / "screenshots"

# ── Drawing helpers ────────────────────────────────────────────────────

RED        = (229, 62,  62)
RED_ALPHA  = (229, 62,  62, 38)    # semi-transparent highlight fill
WHITE      = (255, 255, 255)
BADGE_RED  = (180, 30,  30)
RADIUS     = 8
STROKE     = 3


def _font(size: int):
    """Return a font, falling back to default if truetype not found."""
    for name in ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Verdana.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def draw_callout(draw: ImageDraw.ImageDraw, img: Image.Image,
                 x1: int, y1: int, x2: int, y2: int,
                 number: int, label: str = ""):
    """
    Draw a numbered red callout box over a region.
      - Semi-transparent red fill inside the box
      - Red rounded-rectangle border
      - Filled red circle with white number in top-left corner
    """
    # Create overlay layer for fill
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rounded_rectangle([x1, y1, x2, y2], radius=RADIUS, fill=RED_ALPHA)
    img.alpha_composite(overlay)

    # Border
    draw.rounded_rectangle([x1, y1, x2, y2], radius=RADIUS,
                            outline=RED, width=STROKE)

    # Badge circle
    badge_r = 14
    bx = x1 + badge_r + 2
    by = y1 - badge_r - 2
    draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r],
                 fill=BADGE_RED)
    # Number text
    fnt = _font(14)
    txt = str(number)
    bbox = draw.textbbox((0, 0), txt, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((bx - tw // 2, by - th // 2 - 1), txt, fill=WHITE, font=fnt)

    # Optional label pill
    if label:
        lbl_fnt = _font(12)
        lbl_bbox = draw.textbbox((0, 0), label, font=lbl_fnt)
        lw = lbl_bbox[2] - lbl_bbox[0] + 14
        lh = lbl_bbox[3] - lbl_bbox[1] + 8
        lx, ly = x1 + badge_r * 2 + 6, y1 - lh // 2 - badge_r
        draw.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=4, fill=BADGE_RED)
        draw.text((lx + 7, ly + 4), label, fill=WHITE, font=lbl_fnt)


def annotate(filename_in: str, filename_out: str,
             callouts: list[dict], title: str = ""):
    """Load raw image, draw callouts, save annotated version."""
    src = SS_DIR / filename_in
    if not src.exists():
        print(f"  ⚠  {filename_in} not found — skipping")
        return

    img = Image.open(src).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for c in callouts:
        draw_callout(draw, img,
                     c["x1"], c["y1"], c["x2"], c["y2"],
                     c["n"], c.get("label", ""))

    # Save as RGB PNG
    out = SS_DIR / filename_out
    img.convert("RGB").save(str(out))
    print(f"  ✓  {filename_out}")


# ── Per-screenshot callout definitions ────────────────────────────────
# Coordinates are for a 1440×900 viewport.
# Adjust if the layout shifts (check raw_* PNGs first).

ANNOTATIONS = [

    # 1 ── App Overview ─────────────────────────────────────────────
    dict(
        src="raw_01_app_overview.png",
        dst="01-app-overview.png",
        callouts=[
            dict(n=1, x1=2,   y1=2,   x2=290, y2=115,  label="Chats Panel"),
            dict(n=2, x1=2,   y1=115, x2=290, y2=390,  label="Document Upload"),
            dict(n=3, x1=2,   y1=430, x2=290, y2=895,  label="Memory Panel"),
            dict(n=4, x1=294, y1=2,   x2=1435,y2=45,   label="Header & Badges"),
            dict(n=5, x1=294, y1=45,  x2=1435,y2=165,  label="Pipeline Trace & Config"),
            dict(n=6, x1=490, y1=175, x2=1200,y2=640,  label="Feature Cards Grid"),
            dict(n=7, x1=294, y1=790, x2=1435,y2=865,  label="Query Input Bar"),
        ],
    ),

    # 2 ── Pipeline Config Bar ──────────────────────────────────────
    dict(
        src="raw_02_pipeline_config.png",
        dst="02-pipeline-config.png",
        callouts=[
            dict(n=1, x1=297, y1=133, x2=492,  y2=165, label="Multi-Query Toggle"),
            dict(n=2, x1=430, y1=133, x2=580,  y2=165, label="Self-RAG Toggle"),
            dict(n=3, x1=533, y1=133, x2=700,  y2=165, label="Compression Toggle"),
            dict(n=4, x1=1088,y1=133, x2=1265, y2=165, label="Vector Method"),
            dict(n=5, x1=1267,y1=133, x2=1435, y2=165, label="Merge Method"),
        ],
    ),

    # 3 ── Document Upload ──────────────────────────────────────────
    dict(
        src="raw_03_document_upload.png",
        dst="03-document-upload.png",
        callouts=[
            dict(n=1, x1=4,   y1=118, x2=286, y2=255,  label="Upload Zone"),
            dict(n=2, x1=4,   y1=255, x2=286, y2=395,  label="Doc List with Chunks"),
            dict(n=3, x1=4,   y1=415, x2=286, y2=445,  label="Share Toggle"),
        ],
    ),

    # 4 ── Pipeline Trace ───────────────────────────────────────────
    dict(
        src="raw_04_pipeline_trace.png",
        dst="04-pipeline-trace.png",
        callouts=[
            dict(n=1, x1=294, y1=46,  x2=440,  y2=82,  label="Pipeline Trace Tab"),
            dict(n=2, x1=540, y1=58,  x2=735,  y2=82,  label="Completed in 6.2 s"),
            dict(n=3, x1=294, y1=83,  x2=1435, y2=155, label="Step Chips Timeline"),
            dict(n=4, x1=294, y1=162, x2=700,  y2=640, label="Step Details List"),
        ],
    ),

    # 5 ── Pipeline Trace Step Details ──────────────────────────────
    dict(
        src="raw_05_pipeline_trace_details.png",
        dst="05-pipeline-trace-details.png",
        callouts=[
            dict(n=1, x1=294, y1=168, x2=700,  y2=228, label="Cross-Session Memory Step"),
            dict(n=2, x1=294, y1=290, x2=700,  y2=345, label="Multi-Query Expand Step"),
            dict(n=3, x1=294, y1=408, x2=700,  y2=466, label="Hybrid Search Step"),
            dict(n=4, x1=294, y1=465, x2=700,  y2=525, label="Relevance Grading Step"),
        ],
    ),

    # 6 ── System Architecture ──────────────────────────────────────
    # Image is 1440×1800; phases occupy top ~510px
    dict(
        src="raw_06_system_architecture.png",
        dst="06-system-architecture.png",
        callouts=[
            dict(n=1, x1=222, y1=63,  x2=1435, y2=238, label="Ingestion Phase"),
            dict(n=2, x1=222, y1=260, x2=1435, y2=418, label="Retrieval Phase"),
            dict(n=3, x1=222, y1=435, x2=1435, y2=515, label="Generation Phase"),
            dict(n=4, x1=222, y1=435, x2=410,  y2=515, label="Cross-Chat Memory"),
        ],
    ),

    # 7 ── RAG Answer with Citations ────────────────────────────────
    dict(
        src="raw_07_rag_answer.png",
        dst="07-rag-answer.png",
        callouts=[
            dict(n=1, x1=462, y1=228, x2=1208, y2=498, label="LLM Answer Text"),
            dict(n=2, x1=462, y1=450, x2=1208, y2=495, label="Inline Source Citation"),
            dict(n=3, x1=462, y1=503, x2=1208, y2=600, label="References Section"),
            dict(n=4, x1=1140,y1=2,   x2=1435, y2=44,  label="Chat/Memory Counters"),
        ],
    ),

    # 8 ── Cross-Session Memory ─────────────────────────────────────
    dict(
        src="raw_08_cross_session_memory.png",
        dst="08-cross-session-memory.png",
        callouts=[
            dict(n=1, x1=2,   y1=430, x2=290, y2=535,  label="Memory Panel"),
            dict(n=2, x1=4,   y1=470, x2=286, y2=513,  label="HNSW Session"),
            dict(n=3, x1=4,   y1=516, x2=286, y2=598,  label="More Archived Sessions"),
            dict(n=4, x1=1130,y1=2,   x2=1380,y2=44,   label="Memory Count Badge"),
        ],
    ),
]


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Annotating screenshots in {SS_DIR}\n")
    for spec in ANNOTATIONS:
        annotate(spec["src"], spec["dst"], spec["callouts"])
    print("\n✅  All annotated screenshots saved.")
