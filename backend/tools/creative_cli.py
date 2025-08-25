import argparse
import json
from rich import print

from backend.modules.creative.creative_synthesis_engine import CreativeSynthesisEngine
from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.consciousness.state_manager import state_manager
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime  # ✅ Fallback to UCS
from backend.modules.utils.trace_logger import trace_log_if_available  # Optional trace stub


def run_creative_session(container_id: str, prompt: str, max_depth: int = 3, verbose: bool = False):
    try:
        # ✅ Load container via runtime
        runtime = ContainerRuntime(state_manager=state_manager)
        runtime.load_and_activate_container(container_id)

        container = runtime.get_decrypted_current_container()

        if container is None:
            # Attempt fallback from UCS
            print(f"[yellow]⚠️ ContainerRuntime failed, attempting UCS fallback...[/yellow]")
            container = get_ucs_runtime().get_container(container_id)

        # Validate container
        if not container:
            raise ValueError(f"❌ Container '{container_id}' not found in runtime or UCS.")

        if not isinstance(container, dict):
            raise TypeError(f"❌ Invalid container format for '{container_id}': expected dict, got {type(container).__name__}")

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

        result = engine.run_synthesis(
            glyph=glyph,
            prompt=prompt,
            max_depth=max_depth,
            verbose=verbose,
        )

        # 🧪 Optional trace log output
        trace_log_if_available(result, context="creative_cli")

        print("\n[bold green]Creative Output:[/bold green]")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"[red]Error:[/red] Creative synthesis failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="CreativeCore CLI Tool")
    parser.add_argument("container_id", help="The ID of the symbolic container to use")
    parser.add_argument("prompt", help="The creative prompt or question")
    parser.add_argument("--depth", type=int, default=3, help="Maximum synthesis depth (default: 3)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    run_creative_session(
        container_id=args.container_id,
        prompt=args.prompt,
        max_depth=args.depth,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()