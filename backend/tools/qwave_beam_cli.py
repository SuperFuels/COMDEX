#!/usr/bin/env python3
# File: tools/qwave_beam_cli.py

"""
qwave_beam_cli.py
==================

CLI debugger and visual runtime for QWave symbolic beams.
Allows step-by-step beam processing, SQI scoring, collapse preview,
and SoulLaw status inspection.

Run:
    $ python tools/qwave_beam_cli.py --steps 10 --gpu
"""

import argparse
import time
from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.progress import track

from backend.modules.runtime.beam_queue import get_active_beams
from backend.modules.sqi.sqi_beam_kernel import process_beams
from backend.modules.glyphwave.core.wave_state import WaveState

console = Console()


def render_beam_table(beams):
    table = Table(title="🔬 QWave Beam Debugger")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Phase")
    table.add_column("Amp")
    table.add_column("Coherence")
    table.add_column("SQI")
    table.add_column("Entropy")
    table.add_column("SoulLaw")
    table.add_column("Status")

    for beam in beams:
        sqi = getattr(beam, "sqi_score", "?")
        entropy = getattr(beam, "entropy", "?")
        soullaw = getattr(beam, "soullaw_status", "unknown")
        status = getattr(beam, "status", "new")
        phase = f"{getattr(beam, 'phase', 0.0):.3f}"
        amp = f"{getattr(beam, 'amplitude', 1.0):.3f}"
        coherence = f"{getattr(beam, 'coherence', 1.0):.2f}"
        beam_id = getattr(beam, "id", "unnamed")

        table.add_row(str(beam_id), phase, amp, coherence, str(sqi), str(entropy), soullaw, status)

    return table


def run_cli_loop(steps: int = 10, use_gpu: bool = True, tick_delay: float = 0.5):
    print(Panel("[bold magenta]⚛ QWave Beam CLI Debugger[/bold magenta]\n[grey70]Step through symbolic beam execution.[/grey70]"))

    for tick in track(range(steps), description="[green]Processing beams..."):
        beams = get_active_beams()
        if not beams:
            print("[yellow]No active beams available. Waiting...[/yellow]")
            time.sleep(tick_delay)
            continue

        processed = process_beams(beams)

        table = render_beam_table(processed)
        console.clear()
        console.print(table)

        time.sleep(tick_delay)


def main():
    parser = argparse.ArgumentParser(description="QWave CLI Debugger")
    parser.add_argument("--steps", type=int, default=10, help="Number of ticks to run")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU acceleration (if available)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between ticks (seconds)")
    args = parser.parse_args()

    run_cli_loop(steps=args.steps, use_gpu=args.gpu, tick_delay=args.delay)


if __name__ == "__main__":
    main()