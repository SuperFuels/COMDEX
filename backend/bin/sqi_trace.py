#!/usr/bin/env python3
"""
CLI stability tracer
Shows rolling ΔSQI curve + summary stats.
"""

import time
from rich.console import Console
from rich.live import Live
from rich.table import Table

from backend.modules.sqi.sqi_stability_trace import (
    get_recent_stability_curve,
    get_stability_score
)

console = Console()

def render():
    tbl = Table(title="SQI Stability Trace")

    tbl.add_column("Age (s)")
    tbl.add_column("ΔSQI")
    tbl.add_column("Source")

    data = get_recent_stability_curve()
    now = time.time()

    for e in reversed(data[-10:]):
        tbl.add_row(
            f"{round(now - e['ts'],1)}",
            f"{e['delta']:+.3f}",
            e['source']
        )

    tbl.add_row("---","---","---")
    tbl.add_row("Stability","", f"{get_stability_score()}")

    return tbl

def main():
    with Live(auto_refresh=False) as live:
        while True:
            live.update(render(), refresh=True)
            time.sleep(0.5)

if __name__ == "__main__":
    main()