"""Compose the before/after social card (assets/before_after.png, 1280x640)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .clean import rescue

ROOT = Path(__file__).resolve().parents[1]

BG = "#0f172a"
PANEL = "#1e293b"
RED = "#f87171"
GREEN = "#4ade80"
INK = "#e2e8f0"
DIM = "#94a3b8"
GOLD = "#fbbf24"

BEFORE_ROWS = [
    ("ord 11297",  "6/23/2025",      "QUALITY CRAB CO. ", "$ 18.35"),
    ("ORD-12711",  "45876",          "dominion cafe",     "95.39 USD"),
    ("ord 13104",  "March 22, 2026", "Zenith  HVAC LLC",  "$4,392.00"),
    ("ORD-12616",  "29-Jun-25",      "pembroke law group","$35.20"),
    ("ORD-14684",  "N/A",            "Harbor Light  Inc", "1,287.50 USD"),
    ("",           "04/24/25",       "harbor light church","$12.75"),
]
AFTER_ROWS = [
    ("ORD-11297", "2025-06-23", "Quality Crab",        "$18.35"),
    ("ORD-12711", "2025-08-07", "Dominion Cafe",       "$95.39"),
    ("ORD-13104", "2026-03-22", "Zenith HVAC",         "$43.92"),
    ("ORD-12616", "2025-06-29", "Pembroke Law Group",  "$35.20"),
    ("ORD-14684", "→ quarantined", "Harbor Light Church", ""),
    ("ORD-14702", "2025-04-24", "Harbor Light Church", "$12.75"),
]


def draw_panel(ax, title, color, rows):
    ax.set_facecolor(PANEL)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.04, 0.93, title, color=color, fontsize=15, fontweight="bold",
            family="DejaVu Sans", va="top")
    cols = [0.04, 0.26, 0.52, 0.84]
    for j, h in enumerate(["order_id", "date", "customer", "price"]):
        ax.text(cols[j], 0.80, h, color=DIM, fontsize=9.5, family="monospace")
    for i, row in enumerate(rows):
        y = 0.70 - i * 0.115
        for j, cell in enumerate(row):
            ax.text(cols[j], y, str(cell)[:22], color=INK, fontsize=9.5,
                    family="monospace")


def render(out_name: str, figsize, title_y, sub_y, panel_bottom, panel_h,
           big_y, stats_y, log) -> None:
    fig = plt.figure(figsize=figsize, dpi=100)
    fig.patch.set_facecolor(BG)

    fig.text(0.5, title_y, "Messy Spreadsheet Rescue", color=INK, fontsize=27,
             fontweight="bold", ha="center", va="top")
    fig.text(0.5, sub_y, "the same spreadsheet — before and after one cleaning pipeline",
             color=DIM, fontsize=12.5, ha="center")

    ax_b = fig.add_axes([0.035, panel_bottom, 0.45, panel_h])
    ax_a = fig.add_axes([0.515, panel_bottom, 0.45, panel_h])
    draw_panel(ax_b, "BEFORE — what the client sends", RED, BEFORE_ROWS)
    draw_panel(ax_a, "AFTER — what they get back", GREEN, AFTER_ROWS)

    fig.text(0.5, big_y, f"${log.revenue_recovered:,.0f} revenue recovered",
             color=GOLD, fontsize=21, fontweight="bold", ha="center")
    fig.text(0.5, stats_y,
             f"{log.rows_in:,} rows in  ·  {log.duplicate_rows_removed:,} duplicates removed  ·  "
             f"{log.customer_variants_merged:,} customer variants merged  ·  "
             f"{log.rows_quarantined:,} rows flagged for human review",
             color=DIM, fontsize=11.5, ha="center")

    out = ROOT / "assets" / out_name
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, facecolor=BG)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    _, _, log = rescue(ROOT / "data" / "messy_sales.csv")
    # 2:1 — GitHub social card / README hero
    render("before_after.png", (12.8, 6.4), 0.945, 0.855, 0.24, 0.54,
           0.145, 0.065, log)
    # 4:3 — Upwork Project Catalog gallery (min 1000x750)
    render("upwork_card_4x3.png", (12.8, 9.6), 0.962, 0.900, 0.34, 0.46,
           0.20, 0.12, log)


if __name__ == "__main__":
    main()
