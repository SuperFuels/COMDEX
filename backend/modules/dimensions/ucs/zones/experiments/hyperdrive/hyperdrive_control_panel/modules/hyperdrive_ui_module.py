import time
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

console = Console()

def render_ui(engine):
    """Renders a Rich-based CLI dashboard of the engine's current state."""
    # Resonance Gauge
    gauge = Progress(
        TextColumn("[bold cyan]Resonance"),
        BarColumn(bar_width=40, complete_style="magenta"),
        TextColumn("{task.percentage:>5.2f}%"),
        TimeElapsedColumn(),
        transient=True,
    )
    gauge_task = gauge.add_task("Resonance", total=100, completed=engine.resonance_phase)

    # Drift and Warp Readiness
    drift = compute_drift(engine)
    warp_ready = check_warp_readiness(engine, drift)

    # Engine Status Table
    table = Table.grid(padding=1)
    table.add_column("Parameter", justify="left")
    table.add_column("Value", justify="right")
    table.add_row("Mode", f"{get_engine_mode(engine)}")
    table.add_row("Resonance Phase", f"[cyan]{engine.resonance_phase:.4f}")
    table.add_row("SQI Enabled", f"[green]{engine.sqi_enabled}")
    table.add_row("Particle Count", f"[yellow]{len(engine.particles)}")
    table.add_row("Fields", f"[cyan]{format_fields(engine.fields)}")
    table.add_row("Stage", f"[bold]{engine.stages[engine.current_stage]}")
    table.add_row("Drift (Δ)", f"[yellow]{drift:.5f}")
    table.add_row("Warp Ready", f"[{'green' if warp_ready else 'red'}]{'✅ Ready' if warp_ready else '❌ Not Ready'}")

    # Event Log Panel
    log_panel = Panel("\n".join(engine.resonance_log[-8:]), title="Event Log", border_style="blue")

    # Combine Panels
    return Panel.fit(
        Table.grid().add_row(gauge).add_row(table).add_row(log_panel),
        title="[bold green]Hyperdrive Engine: SQI-Controlled"
    )

def get_engine_mode(engine):
    """Infer engine operational mode with color-coded phases."""
    if engine.resonance_phase < 85:
        return "[cyan]Stabilizing"
    elif 85 <= engine.resonance_phase < 99:
        return "[green]Propulsion"
    elif 99 <= engine.resonance_phase < 100:
        return "[yellow]Warp Threshold"
    return "[magenta]Warp Bubble Engaged"

def compute_drift(engine):
    """Compute resonance drift from recent filtered data."""
    if not engine.resonance_filtered:
        return 0.0
    window = engine.resonance_filtered[-30:]
    return max(window) - min(window)

def check_warp_readiness(engine, drift):
    """
    Warp readiness requires:
    - Low drift (SQI stabilized)
    - Resonance >= 99 (near warp threshold)
    - Optional: Harmonic coherence if available
    """
    harmonic_lock = getattr(engine, "harmonic_lock", True)  # Default to True if not implemented
    return drift < engine.stability_threshold * 0.5 and engine.resonance_phase >= 99 and harmonic_lock

def format_fields(fields):
    """Format engine fields neatly for UI display."""
    return ", ".join([f"{k}: {v:.3f}" for k, v in fields.items()])

def run_ui(engine):
    """Continuously render engine dashboard."""
    with Live(render_ui(engine), refresh_per_second=10) as live:
        while True:
            live.update(render_ui(engine))
            time.sleep(0.1)