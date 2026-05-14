"""
Resonant Network Live Monitor
──────────────────────────────
Displays live ψ-κ-T-Φ metrics and Δφ/Δσ coherence drift
for AION_CORE, QQC_CORE, and any other active nodes.

Reads continuously from:
    backend/logs/morphic_ingest_backup.jsonl

Usage:
    PYTHONPATH=. python backend/AION/system/network_sync/resonant_monitor.py
"""

import curses
import json
import time
from pathlib import Path
from datetime import datetime

STATE_FILE = Path("backend/logs/morphic_ingest_backup.jsonl")

# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────
def tail_jsonl(path, last_pos):
    """Read new JSONL entries from file since last read."""
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.seek(last_pos)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            pos = f.tell()
        return entries, pos
    except FileNotFoundError:
        return [], last_pos


def classify_state(dphi, dsigma):
    """Return coherence classification string and color index."""
    drift = abs(dphi)
    coh_dev = abs(dsigma)
    if drift < 0.03 and coh_dev < 0.02:
        return "Stable", 2
    elif drift < 0.07:
        return "Minor Drift", 3
    elif drift < 0.15:
        return "Phase Drift", 4
    else:
        return "Desync", 5


def safe_addstr(window, y, x, text, color=None):
    """Write safely within window boundaries."""
    max_y, max_x = window.getmaxyx()
    if y >= max_y:
        return  # out of bounds vertically
    if len(text) + x >= max_x:
        text = text[: max_x - x - 1]
    try:
        if color:
            window.addstr(y, x, text, color)
        else:
            window.addstr(y, x, text)
    except curses.error:
        pass  # ignore boundary overflows


def render_node(window, y, node, data):
    try:
        metrics = data.get("metrics", {})
        deltas = data.get("deltas", {})

        phi = metrics.get("phi", 0.0)
        psi = metrics.get("psi", 0.0)
        kappa = metrics.get("kappa", 0.0)
        T = metrics.get("T", 0.0)
        role = data.get("role", "?")
        dphi = deltas.get("dphi", 0.0)
        dsigma = deltas.get("dsigma", 0.0)

        state, color_idx = classify_state(dphi, dsigma)
        color = curses.color_pair(color_idx)

        line = (
            f"{node:<10} | role={role:<8} φ={phi:6.3f} ψ={psi:6.3f} κ={kappa:6.3f} "
            f"T={T:6.3f} Δφ={dphi:6.3f} Δσ={dsigma:6.3f}  [{state}]"
        )
        safe_addstr(window, y, 2, line, color)
    except Exception as e:
        safe_addstr(window, y, 2, f"[Error rendering {node}: {e}]", curses.color_pair(5))


# ───────────────────────────────────────────────
# Main Display Loop
# ───────────────────────────────────────────────
def main(screen):
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # base
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # stable
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # minor drift
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)# phase drift
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)    # desync/error

    last_pos = 0
    nodes = {}

    while True:
        entries, last_pos = tail_jsonl(STATE_FILE, last_pos)
        for e in entries:
            nodes[e.get("node_id", "unknown")] = e

        if nodes:
            avg_dphi = sum(abs(n.get("deltas", {}).get("dphi", 0)) for n in nodes.values()) / len(nodes)
            avg_dsigma = sum(abs(n.get("deltas", {}).get("dsigma", 0)) for n in nodes.values()) / len(nodes)
        else:
            avg_dphi = avg_dsigma = 0

        screen.erase()
        safe_addstr(screen, 1, 2, "🌐 Resonant Network Live Monitor", curses.color_pair(1) | curses.A_BOLD)
        safe_addstr(screen, 2, 2, f"Updated: {datetime.now().strftime('%H:%M:%S')}")
        safe_addstr(screen, 3, 2, f"Nodes: {len(nodes)}   ⌀Δφ={avg_dphi:6.3f}   ⌀Δσ={avg_dsigma:6.3f}")
        safe_addstr(screen, 5, 2, "Node         |   φ      ψ      κ      T         Δφ      Δσ     State")
        safe_addstr(screen, 6, 2, "──────────────────────────────────────────────────────────────────────────────────────────")

        y = 7
        for node, data in nodes.items():
            render_node(screen, y, node, data)
            y += 1
            if y >= curses.LINES - 2:
                break  # prevent overflow

        screen.refresh()
        time.sleep(1.5)


if __name__ == "__main__":
    curses.wrapper(main)