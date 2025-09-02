import os
import time
import asyncio
import json
import logging
from tqdm import tqdm

from backend.modules.codex.codex_ast_encoder import (
    parse_codexlang_to_ast,
    encode_codex_ast_to_glyphs
)
from backend.modules.symbolic.symbolic_ingestion_engine import run_full_symbolic_pipeline
from backend.modules.runtime.container_runtime import (
    ContainerRuntime,
    safe_load_container_by_id,
)
from backend.modules.consciousness.state_manager import DummyStateManager

# ✅ Source CodexLang input file (not Python!)
TEST_PATH = "backend/tests/test_glyphlogic_module.py"
TEST_CONTAINER_ID = "kg_writer_test"
CONTAINER_OUTPUT_PATH = "backend/modules/dimensions/containers/kg_writer_test.dc.json"

def wrap_as_dc_container(code: str) -> dict:
    """Wrap source code as a .dc.json container for symbolic ingestion."""
    return {
        "id": TEST_CONTAINER_ID,
        "type": "sourcecode",
        "format": "codexlang",
        "entrypoint": "main",
        "source": code,
        "meta": {
            "title": "KG Writer Compression Test",
            "description": "Benchmark symbolic ingestion on test_glyphlogic_module.codex"
        },
        "trace": {}
    }

def run_kg_writer_compression_benchmark():
    """Benchmark symbolic compression on a CodexLang source file."""
    logging.info(f"📂 Loading source file: {TEST_PATH}")
    start_time = time.time()

    # ✅ Step 1: Read raw CodexLang source
    with open(TEST_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()
    duration_read = time.time() - start_time
    logging.info(f"✅ File read complete in {duration_read:.2f}s")

    # ✅ Step 2: Ensure container directory exists
    os.makedirs(os.path.dirname(CONTAINER_OUTPUT_PATH), exist_ok=True)

    # ✅ Step 3: Wrap + parse to AST + encode to glyphs
    container = wrap_as_dc_container(source_code)
    try:
        ast = parse_codexlang_to_ast(source_code)
        logging.info("✅ AST parsed successfully")
    except Exception as e:
        logging.error(f"❌ AST parsing failed: {e}")
        return
    glyphs = encode_codex_ast_to_glyphs(ast)
    container["trace"]["logic"] = glyphs

    # ✅ Step 4: Save container using runtime
    runtime = ContainerRuntime(state_manager=DummyStateManager())
    runtime.state_manager.set_current_container(container)
    runtime.save_container()
    logging.info(f"📦 Container saved via runtime")

    # ✅ Additionally save raw container to file
    with open(CONTAINER_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2)
    logging.info(f"📝 Raw container written to: {CONTAINER_OUTPUT_PATH}")

    # ✅ Step 5: Run full symbolic pipeline
    start_time = time.time()
    run_full_symbolic_pipeline(TEST_CONTAINER_ID)
    duration_compress = time.time() - start_time
    logging.info(f"🧠 Compression completed in {duration_compress:.2f}s")

    # ✅ Step 6: Reload + summarize results
    container = safe_load_container_by_id(TEST_CONTAINER_ID)
    trace = container.get("trace", {})
    logic_count = len(trace.get("logic", []))
    replay_count = len(trace.get("replayPaths", []))
    glyph_count = len(container.get("glyphs", []))
    logging.info(f"📊 Final stats — Logic: {logic_count}, Glyphs: {glyph_count}, Traces: {replay_count}")

async def async_run():
    logging.basicConfig(level=logging.INFO)
    logging.info(f"[STATE] Current container set to: {TEST_CONTAINER_ID}")

    for _ in tqdm(range(1), desc="Batches"):
        run_kg_writer_compression_benchmark()

if __name__ == "__main__":
    asyncio.run(async_run())