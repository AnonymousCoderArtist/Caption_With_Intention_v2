"""Generate M4 feature checklist infographic."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, axes = plt.subplots(1, 2, figsize=(16, 10))
fig.patch.set_facecolor("#0a0a1a")

YELLOW = "#E5E517"
CYAN = "#17E5E5"
WHITE = "#FFFFFF"
GRAY = "#888888"
CARD_BG = "#16213e"
GREEN = "#17E517"

# --- Left panel: Sync Engine Features ---
ax1 = axes[0]
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 10)
ax1.axis("off")
ax1.set_facecolor("#0a0a1a")

ax1.text(5, 9.5, "Synchronization Engine", ha="center", fontsize=14,
         fontweight="bold", color=YELLOW)
ax1.text(5, 9.1, "Spec 4.2", ha="center", fontsize=10, color=GRAY)

features_sync = [
    ("Read-Ahead Layer", "Full sentence, white, 90% opacity", True),
    ("Word-Onset Color Sync", "Speaker color at word START", True),
    ("Pop Animation", "15% scale at word onset", True),
    ("Roman/Italic", "Italic for off-camera", True),
    ("Max 2 Lines", "Enforced per event", True),
    ("Dynamic Box Sizing", "Adapts to content", True),
]

y_pos = 8.3
for title, desc, status in features_sync:
    card = FancyBboxPatch((0.5, y_pos - 0.7), 9, 0.8,
                          boxstyle="round,pad=0.05,rounding_size=0.1",
                          facecolor=CARD_BG, edgecolor=GREEN if status else GRAY, linewidth=1.5)
    ax1.add_patch(card)
    symbol = "✓" if status else "○"
    color = GREEN if status else GRAY
    ax1.text(0.8, y_pos - 0.35, symbol, fontsize=14, color=color, fontweight="bold")
    ax1.text(1.3, y_pos - 0.2, title, fontsize=9.5, color=WHITE, fontweight="bold")
    ax1.text(1.3, y_pos - 0.55, desc, fontsize=7.5, color=GRAY)
    y_pos -= 1.1

# --- Right panel: Visual Rules ---
ax2 = axes[1]
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis("off")
ax2.set_facecolor("#0a0a1a")

ax2.text(5, 9.5, "Visual Rules", ha="center", fontsize=14,
         fontweight="bold", color=CYAN)
ax2.text(5, 9.1, "Spec 4.3 & 5", ha="center", fontsize=10, color=GRAY)

features_visual = [
    ("Type Size Range", "3% - 12% screen height", True),
    ("Baseline Size", "5% screen height", True),
    ("Pitch to Weight", "80-160Hz heavy, 200+Hz light", True),
    ("Harmonics to Width", "Low wide, high narrow", True),
    ("Caption Box", "90% black, behind text", True),
    ("Work Area", "Lower 20% frame", True),
    ("SFX Rules", "White, [brackets], no color", True),
    ("Music Rules", "White, symbol, no animation", True),
]

y_pos = 8.3
for title, desc, status in features_visual:
    card = FancyBboxPatch((0.5, y_pos - 0.7), 9, 0.8,
                          boxstyle="round,pad=0.05,rounding_size=0.1",
                          facecolor=CARD_BG, edgecolor=GREEN if status else GRAY, linewidth=1.5)
    ax2.add_patch(card)
    symbol = "✓" if status else "○"
    color = GREEN if status else GRAY
    ax2.text(0.8, y_pos - 0.35, symbol, fontsize=14, color=color, fontweight="bold")
    ax2.text(1.3, y_pos - 0.2, title, fontsize=9.5, color=WHITE, fontweight="bold")
    ax2.text(1.3, y_pos - 0.55, desc, fontsize=7.5, color=GRAY)
    y_pos -= 0.9

# Bottom status bar
fig.text(0.5, 0.05, "M4: Deterministic CI Renderer  -  256/256 tests passing  -  7/7 verification checks passing",
         ha="center", fontsize=10, color=YELLOW, fontweight="bold",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a2e", edgecolor=YELLOW, linewidth=2))

plt.tight_layout(rect=[0, 0.08, 1, 1])
plt.savefig("docs/m4-feature-checklist.png", dpi=150, bbox_inches="tight",
            facecolor="#0a0a1a", edgecolor="none")
print("Generated docs/m4-feature-checklist.png")
