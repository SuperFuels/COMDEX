import argparse
import json
from rich import print
import logging
from datetime import datetime  

logger = logging.getLogger(__name__)

from backend.modules.creative.creative_synthesis_engine import CreativeSynthesisEngine
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.consciousness.state_manager import state_manager
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.utils.trace_logger import trace_log_if_available

# 🧠 HST + WebSocket tools
from backend.modules.symbolic.symbol_tree_generator import build_symbolic_tree_from_container, inject_symbolic_tree
from backend.modules.dna_chain.dc_handler import load_dc_container
from backend.modules.symbolic.hst.hst_websocket_streamer import stream_hst_to_websocket

# 🧠 SQI Scoring
from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container


def print_top_electrons_by_sqi(container: dict, top_n: int = 3):
    electrons = container.get("electrons", [])
    if not electrons:
        print("[yellow]⚠️ No electrons found in container[/yellow]")
        return

    scored = []
    for e in electrons:
        score = e.get("sqi_score")
        if score is not None:
            scored.append((score, e.get("label") or e.get("id") or "unnamed"))

    if not scored:
        print("[yellow]⚠️ No SQI scores found in electrons[/yellow]")
        return

    scored.sort(reverse=True)
    print(f"[cyan]📊 Top {top_n} Electrons by SQI:[/cyan]")
    for i, (score, label) in enumerate(scored[:top_n]):
        print(f"  {i+1}. {label} - SQI: {score:.4f}")


def run_creative_session(container_id: str, prompt: str, max_depth: int = 3, verbose: bool = False, inject_sqi: bool = False):
    try:
        # ✅ Load container via runtime
        runtime = ContainerRuntime(state_manager=state_manager)
        runtime.load_and_activate_container(container_id)

        container = runtime.get_decrypted_current_container()

        if container is None:
            print(f"[yellow]⚠️ ContainerRuntime failed, attempting UCS fallback...[/yellow]")
            container = get_ucs_runtime().get_container(container_id)

        # Validate container
        if not container:
            raise ValueError(f"❌ Container '{container_id}' not found in runtime or UCS.")

        if not isinstance(container, dict):
            raise TypeError(f"❌ Invalid container format for '{container_id}': expected dict, got {type(container).__name__}")

        # 🧠 SQI Injection (optional pre-pass)
        if inject_sqi:
            try:
                inject_sqi_scores_into_container(container)
                print("[green]✅ SQI scores injected into container electrons[/green]")
                print_top_electrons_by_sqi(container)
            except Exception as sqi_err:
                print(f"[yellow]⚠️ SQI injection failed: {sqi_err}[/yellow]")

    except Exception as e:
        print(f"[red]Error:[/red] Failed to load container '{container_id}': {e}")
        return

    try:
        # 🧠 Run Creative Synthesis
        engine = CreativeSynthesisEngine(container)

        glyph = (
            container.get("entrypoint")
            or container.get("symbol")
            or container.get("meta", {}).get("symbol")
            or {"type": "symbol", "label": "fallback"}
        )

        # 🛠️ FORCE-INJECT name field if missing
        if "name" not in glyph:
            glyph["name"] = glyph.get("label", "fallback")

        # 🔍 Log the glyph to diagnose
        print(f"[blue]🔍 Using glyph for synthesis:[/blue] {json.dumps(glyph, indent=2)}")

        result = engine.run_synthesis(
            glyph=glyph,
            prompt=prompt,
            max_depth=max_depth,
            verbose=verbose,
        )

        # ✅ Fix: Ensure required fields are present in result to prevent downstream errors
        if "name" not in result:
            result["name"] = result.get("label") or result.get("symbol") or "Unnamed Synthesis"
        if "created_on" not in result:
            result["created_on"] = result.get("metadata", {}).get("created_on") or datetime.utcnow().isoformat()

        # 🧪 Optional trace log output
        trace_log_if_available(result, context="creative_cli")

        print("\n[bold green]Creative Output:[/bold green]")
        print(json.dumps(result, indent=2))

        # 🔁 Re-inject SQI after mutation
        if inject_sqi:
            try:
                inject_sqi_scores_into_container(container)
                print("\n[green]🔁 Re-injected SQI scores after synthesis[/green]")
                print_top_electrons_by_sqi(container)
            except Exception as sqi_err:
                print(f"[yellow]⚠️ SQI re-injection failed: {sqi_err}[/yellow]")

        # 🌲 Inject Holographic Symbol Tree (HST) after synthesis
        try:
            if isinstance(container_id, str) and container_id.startswith(("dc_", "atom_", "hoberman_")):
                container_obj = load_dc_container(container_id)
                tree = build_symbolic_tree_from_container(container_obj)
                inject_symbolic_tree(container_id, tree)
                print(f"\n[cyan]✅ HST injected for {container_id} with {len(tree.node_index)} nodes[/cyan]")

                # 🌐 Stream to GHX/QFC via WebSocket
                stream_hst_to_websocket(
                    container_id=container_id,
                    context="creative_cli"
                )

        except Exception as hst_err:
            print(f"[yellow]⚠️ HST injection or streaming failed: {hst_err}[/yellow]")

    except Exception as e:
        print(f"[red]Error:[/red] Creative synthesis failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="CreativeCore CLI Tool")
    parser.add_argument("container_id", help="The ID of the symbolic container to use")
    parser.add_argument("prompt", help="The creative prompt or question")
    parser.add_argument("--depth", type=int, default=3, help="Maximum synthesis depth (default: 3)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--inject-sqi", action="store_true", help="Inject SQI scores before and after synthesis")

    args = parser.parse_args()

    run_creative_session(
        container_id=args.container_id,
        prompt=args.prompt,
        max_depth=args.depth,
        verbose=args.verbose,
        inject_sqi=args.inject_sqi,
    )


if __name__ == "__main__":
    main()