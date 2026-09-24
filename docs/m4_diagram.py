"""Generate M4 renderer architecture diagram as PNG."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis("off")
fig.patch.set_facecolor("#0a0a1a")

# Colors
YELLOW = "#E5E517"
CYAN = "#17E5E5"
RED = "#E51717"
WHITE = "#FFFFFF"
GRAY = "#666666"
DARK_BG = "#1a1a2e"
CARD_BG = "#16213e"
ACCENT = "#E85C2E"

def draw_card(ax, x, y, w, h, title, color, subtext="", title_color=WHITE):
    card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
                          facecolor=CARD_BG, edgecolor=color, linewidth=2)
    ax.add_patch(card)
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=11,
            fontweight="bold", color=title_color)
    if subtext:
        ax.text(x + w / 2, y + h - 0.65, subtext, ha="center", va="top", fontsize=8,
                color=GRAY, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color=YELLOW, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=2,
                                connectionstyle="arc3,rad=0"))
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        ax.text(mx, my + 0.15, label, ha="center", va="bottom", fontsize=7,
                color=color, fontweight="bold")

# Title
ax.text(8, 11.5, "M4 — Deterministic CI Renderer", ha="center", va="center",
        fontsize=18, fontweight="bold", color=YELLOW)
ax.text(8, 11.1, "Synchronization Engine + Visual Rules", ha="center", va="center",
        fontsize=11, color=GRAY)

# Row 1: Input
draw_card(ax, 0.5, 9.8, 3.5, 0.9, "Source Video", RED, "mp4 / mov / mkv")
draw_card(ax, 5.5, 9.8, 5.5, 0.9, "Project JSON", CYAN, "events, speakers, words, styles")
draw_card(ax, 12.5, 9.8, 3, 0.9, "Design System v1.0", YELLOW, "JSON profiles")

# Row 2: CwiRenderer
draw_card(ax, 0.5, 8.0, 15, 1.2, "CwiRenderer Engine", YELLOW, "Burns styled captions into video", CYAN)

# Row 3: Synchronization Engine (highlighted)
draw_card(ax, 0.5, 6.3, 4.8, 1.3, "Synchronization Engine", YELLOW, "Read-ahead + Color Sync + Pop", CYAN)
# Sub-features
ax.text(0.7, 6.0, "• Read-ahead (white 90%)", fontsize=8, color=WHITE, va="center")
ax.text(0.7, 5.75, "• Word-onset color sync", fontsize=8, color=WHITE, va="center")
ax.text(0.7, 5.5, "• Pop animation (15%)", fontsize=8, color=WHITE, va="center")

draw_card(ax, 5.5, 6.3, 4.8, 1.3, "Intonation Engine", CYAN, "Size / Weight / Width mapping", YELLOW)
ax.text(5.7, 6.0, "• Volume → size (3-12%)", fontsize=8, color=WHITE, va="center")
ax.text(5.7, 5.75, "• Pitch → weight", fontsize=8, color=WHITE, va="center")
ax.text(5.7, 5.5, "• Harmonics → width", fontsize=8, color=WHITE, va="center")

draw_card(ax, 10.5, 6.3, 5, 1.3, "Event Router", ACCENT, "dialogue / sfx / music", WHITE)
ax.text(10.7, 6.0, "• dialogue → sync engine", fontsize=8, color=WHITE, va="center")
ax.text(10.7, 5.75, "• sound_effect → white/brackets", fontsize=8, color=WHITE, va="center")
ax.text(10.7, 5.5, "• music → white/symbol", fontsize=8, color=WHITE, va="center")

# Row 4: ASS Pipeline
draw_card(ax, 0.5, 4.6, 7, 1.3, "ASS Export Pipeline", CYAN, "Plain text → AssExporter → Inject tags", YELLOW)
ax.text(0.7, 4.3, "1. Build plain text + tag metadata", fontsize=8, color=WHITE, va="center")
ax.text(0.7, 4.05, "2. AssExporter (escapes text properly)", fontsize=8, color=WHITE, va="center")
ax.text(0.7, 3.8, "3. Inject ASS override tags (no double-escape)", fontsize=8, color=WHITE, va="center")

draw_card(ax, 8, 4.6, 7.5, 1.3, "Style Injection", YELLOW, "90% black box + work area + font", CYAN)
ax.text(8.2, 4.3, "• Caption box: 90% black", fontsize=8, color=WHITE, va="center")
ax.text(8.2, 4.05, "• Work area: lower 20%", fontsize=8, color=WHITE, va="center")
ax.text(8.2, 3.8, "• Font: Roboto Flex", fontsize=8, color=WHITE, va="center")

# Row 5: Output
draw_card(ax, 3, 2.6, 10, 1.3, "FFmpeg Burn-in", RED, "subtitles filter + stream copy audio", WHITE)

draw_card(ax, 0.5, 0.8, 7, 1.3, "[OUTPUT] Burned-in CI Video", YELLOW, "Burned-in CI captions", CYAN)
draw_card(ax, 8, 0.8, 7.5, 1.3, "[SIDECAR] Export Formats", CYAN, "SRT / VTT / TTML / ASS", YELLOW)

# Arrows
draw_arrow(ax, 2.2, 9.8, 2.2, 8.8)
draw_arrow(ax, 8.2, 9.8, 8.2, 8.8)
draw_arrow(ax, 14, 9.8, 14, 8.8)
draw_arrow(ax, 1.2, 8.0, 1.2, 7.6)
draw_arrow(ax, 8, 7.6, 3, 7.0)
draw_arrow(ax, 8, 7.6, 8, 5.9)
draw_arrow(ax, 12, 7.6, 13, 7.0)
draw_arrow(ax, 3, 6.3, 3, 5.9)
draw_arrow(ax, 8, 6.3, 8, 5.9)
draw_arrow(ax, 13, 6.3, 13, 5.9)
draw_arrow(ax, 4, 5.2, 4, 4.6)
draw_arrow(ax, 10.5, 5.2, 11, 4.6)
draw_arrow(ax, 4, 4.6, 4, 3.9)
draw_arrow(ax, 11, 4.6, 11, 3.9)
draw_arrow(ax, 6, 3.3, 6, 3.2)
draw_arrow(ax, 14, 3.3, 14, 3.2)
draw_arrow(ax, 6.5, 3.2, 6.5, 2.6)
draw_arrow(ax, 13.5, 3.2, 13.5, 2.6)
draw_arrow(ax, 5, 2.6, 5, 2.1)
draw_arrow(ax, 14, 2.6, 14, 2.1)

# Legend
ax.text(8, 0.3, "Legend:  Yellow=CWI  Cyan=Engine  Red=I/O  Orange=Router",
        ha="center", va="center", fontsize=8, color=GRAY, style="italic")

plt.tight_layout()
plt.savefig("docs/m4-renderer-architecture.png", dpi=150, bbox_inches="tight",
            facecolor="#0a0a1a", edgecolor="none")
print("Generated docs/m4-renderer-architecture.png")
