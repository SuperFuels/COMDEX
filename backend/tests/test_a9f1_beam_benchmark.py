
import time
import pytest
import random
import datetime
from pathlib import Path
import matplotlib.pyplot as plt

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.sqi.sqi_beam_kernel import process_beams
from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.modules.sqi.sqi_scorer import score_electron_glyph as compute_sqi_score

TOTAL_BEAMS = 1000
BATCH_SIZE = 250
MAX_DEPTH = 14
ENABLE_PLOT = True

OUTPUT_DIR = Path("a9f1_batches")
OUTPUT_DIR.mkdir(exist_ok=True)

ops = ["⊕", "⟲", "↔", "→", "⧖"]
op_weights = [4, 2, 1, 2, 5]  # Compression/contradiction bias

def log(msg: str, file=None):
    print(msg)
    if file:
        with open(file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

def generate_random_qglyph_tree(depth=0, max_depth=MAX_DEPTH):
    if depth >= max_depth:
        return f"X{random.randint(1, 99)}"
    op = random.choices(ops, weights=op_weights)[0]
    return {
        op: [
            generate_random_qglyph_tree(depth + 1, max_depth),
            generate_random_qglyph_tree(depth + 1, max_depth)
        ]
    }

def mutate_logic(logic, depth=0):
    if isinstance(logic, dict):
        op = list(logic.keys())[0]
        children = logic[op]
        if random.random() < 0.5:
            op = random.choices(ops, weights=op_weights)[0]
        return {op: [mutate_logic(children[0], depth + 1), mutate_logic(children[1], depth + 1)]}
    return logic

def make_test_beams(n):
    beams = []
    for i in range(n):
        beam = WaveState(
            wave_id=f"beam_{random.randint(0, 999999)}",
            glyph_data={"source": f"test_beam", "target": "benchmark_target"},
            glyph_id=f"test_glyph_{random.randint(0, 999999)}",
            source="test_beam",
            target="benchmark_target",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z"
        )
        beam.logic = mutate_logic(generate_random_qglyph_tree())
        beam.status = "pending"
        beam.coherence = random.uniform(0.2, 1.0)
        beams.append(beam)
    return beams

@pytest.mark.asyncio
async def test_a9f1_sycamore_beam_autotune_batched():
    output_file = OUTPUT_DIR / f"autotune_output_{TOTAL_BEAMS}.txt"
    if output_file.exists():
        output_file.unlink()

    all_scores, all_entropies, all_ratios, all_sqis = [], [], [], []
    global_min_sqi, global_max_sqi = float("inf"), float("-inf")
    global_min_id, global_max_id = None, None
    total_duration = 0.0

    log(f"\n🚀 A9f1 Autotuned Benchmark | {TOTAL_BEAMS} beams in batches of {BATCH_SIZE}\n", output_file)

    for batch_num in range((TOTAL_BEAMS // BATCH_SIZE)):
        log(f"🔁 Batch {batch_num + 1}/{TOTAL_BEAMS // BATCH_SIZE}", output_file)
        beams = make_test_beams(BATCH_SIZE)
        start = time.perf_counter()
        processed = process_beams(beams)
        duration = time.perf_counter() - start
        total_duration += duration

        for i, beam in enumerate(processed):
            try:
                score = score_glyph_tree(beam.logic)
                entropy = len(str(beam.logic))
                simulated_glyph = {
                    "id": beam.glyph_id,
                    "label": beam.glyph_data["source"],
                    "type": "electron",
                    "logic_trace": [{
                        "confidence": round(random.uniform(0.3, 1.0), 3),
                        "entropy": round(random.uniform(0.0, 1.0), 3),
                        "status": random.choice(["valid", "unknown", "contradiction", "simplify"]),
                    }]
                }
                sqi = compute_sqi_score(simulated_glyph)
            except Exception as e:
                log(f"[{i}] ❌ Error scoring beam {beam.wave_id}: {e}", output_file)
                continue

            all_scores.append(score)
            all_entropies.append(entropy)
            all_ratios.append(entropy / score if score else 0.0)
            all_sqis.append(sqi)

            if sqi < global_min_sqi:
                global_min_sqi = sqi
                global_min_id = beam.wave_id
            if sqi > global_max_sqi:
                global_max_sqi = sqi
                global_max_id = beam.wave_id

        del beams  # Free memory per batch

    avg_score = sum(all_scores) / len(all_scores)
    avg_entropy = sum(all_entropies) / len(all_entropies)
    compression_ratio = round(avg_entropy / avg_score, 4)

    log(f"\n⏱️ Total Time: {total_duration * 1000:.2f} ms", output_file)
    log(f"🧮 Per Beam: {total_duration * 1000 / TOTAL_BEAMS:.3f} ms", output_file)
    log(f"📊 Avg Score: {avg_score:.2f}", output_file)
    log(f"🌀 Avg Entropy: {avg_entropy:.2f}", output_file)
    log(f"🔁 Compression Ratio: {compression_ratio}x", output_file)
    log(f"📉 Lowest SQI: {global_min_sqi:.3f} (Beam: {global_min_id})", output_file)
    log(f"📈 Highest SQI: {global_max_sqi:.3f} (Beam: {global_max_id})", output_file)

    if ENABLE_PLOT:
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("A9f1 Autotuned Beam Benchmark Metrics")

        axs[0, 0].hist(all_scores, bins=30, color="blue")
        axs[0, 0].set_title("Symbolic Score Distribution")

        axs[0, 1].hist(all_entropies, bins=30, color="green")
        axs[0, 1].set_title("Entropy Distribution")

        axs[1, 0].scatter(range(len(all_ratios)), all_ratios, color="purple", s=4)
        axs[1, 0].set_title("Compression Ratio per Beam")

        axs[1, 1].hist(all_sqis, bins=30, color="orange")
        axs[1, 1].set_title("SQI Score Distribution")

        plt.tight_layout()
        plot_path = OUTPUT_DIR / f"autotune_plot_{TOTAL_BEAMS}.png"
        plt.savefig(plot_path)
        log(f"📉 Saved plot to: {plot_path}\n", output_file)

    assert len(all_scores) == TOTAL_BEAMS
    assert total_duration < 120.0