import json
from pathlib import Path
from rich import print
from rich.table import Table
from rich.console import Console
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MODULE_DIR = Path(__file__).resolve().parent
PHASE_SUMMARY_FILE = MODULE_DIR / "aion_phase_summary.json"
MILESTONE_FILE = MODULE_DIR / "aion_milestones.json"
PHASE_LOG_FILE = MODULE_DIR / "aion_phase_log.json"

console = Console()

def load_json(path):
    if not path.exists():
        print(f"[red]Missing:[/red] {path}")
        return {}
    with open(path) as f:
        return json.load(f)

def render_summary():
    data = load_json(PHASE_SUMMARY_FILE)
    if not data:
        return

    print(f"\n🌱 [bold cyan]AION Phase Summary[/bold cyan] - Last Updated: [grey]{data.get('last_updated', 'n/a')}[/grey]")
    print(f"📈 Phase: [green]{data.get('current_phase')}[/green]")
    print(f"✅ Unlocked Modules: [green]{', '.join(data.get('unlocked_modules', []))}[/green]")
    print(f"🔒 Locked Modules: [yellow]{', '.join(data.get('locked_modules', []))}[/yellow]")
    print(f"🧩 Total Milestones: [bold]{data.get('milestone_count')}[/bold]")

def render_milestones():
    milestones = load_json(MILESTONE_FILE).get("milestones", [])
    if not milestones:
        print("[italic]No milestones found.[/italic]")
        return

    table = Table(title="📜 Milestone Timeline")
    table.add_column("No.", style="dim", width=4)
    table.add_column("Name", style="cyan")
    table.add_column("Time", style="white")
    table.add_column("Source", style="magenta")

    for i, m in enumerate(milestones, 1):
        table.add_row(str(i), m["name"], m["timestamp"], m.get("source", "manual"))

    console.print(table)

def render_phase_log():
    logs = load_json(PHASE_LOG_FILE)
    if not logs:
        print("[italic]No phase transitions logged.[/italic]")
        return

    table = Table(title="🔄 Phase Change Log")
    table.add_column("From", style="red")
    table.add_column("To", style="green")
    table.add_column("Reason", style="yellow")
    table.add_column("Time", style="white")

    for entry in logs:
        table.add_row(
            entry.get("from", "?"),
            entry.get("to", "?"),
            entry.get("reason", "—"),
            entry.get("timestamp", "")
        )

    console.print(table)

if __name__ == "__main__":
    render_summary()
    render_milestones()
    print()
    render_phase_log()