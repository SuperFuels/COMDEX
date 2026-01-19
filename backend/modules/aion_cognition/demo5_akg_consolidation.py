# backend/modules/aion_cognition/demo5_akg_consolidation.py
from __future__ import annotations

import argparse, os, time, json
from typing import List, Tuple, Dict, Any

from .akg_triplets import AKGTripletStore
from .telemetry_io import write_qdata
from .akg_graph_export import export_akg_graph

Triplet = Tuple[str, str, str]

def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _load_lexmemory_pairs(path: str) -> List[Triplet]:
    """
    Best-effort loader.
    Supports:
      - { "entries": [ {prompt/answer}, ... ] }
      - { "<prompt>": { "answer": ... }, ... }
      - [ {prompt, answer}, ... ]
    Produces (prompt, "answer_is", answer)
    """
    if not os.path.exists(path):
        return []

    try:
        raw = _load_json(path)
    except Exception:
        return []

    triplets: List[Triplet] = []

    def pull_pa(obj: Dict[str, Any]) -> Tuple[str, str]:
        p = (obj.get("prompt") or obj.get("q") or obj.get("question") or "").strip()
        a = (obj.get("answer") or obj.get("a") or obj.get("response") or "").strip()
        return p, a

    if isinstance(raw, dict):
        entries = raw.get("entries")
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict):
                    p, a = pull_pa(e)
                    if p and a:
                        triplets.append((p, "answer_is", a))
            return triplets

        # dict mapping prompt -> {answer:...}
        for p, v in raw.items():
            if isinstance(v, dict):
                a = (v.get("answer") or v.get("a") or "").strip()
                if (p or "").strip() and a:
                    triplets.append((p.strip(), "answer_is", a))
        return triplets

    if isinstance(raw, list):
        for e in raw:
            if isinstance(e, dict):
                p, a = pull_pa(e)
                if p and a:
                    triplets.append((p, "answer_is", a))
        return triplets

    return []

def _plot_strengths(out_png: str, labels: List[str], strengths: List[float]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    plt.figure()
    plt.bar(range(len(strengths)), strengths)
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.ylabel("edge_strength (0..1)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.35)
    ap.add_argument("--half-life-s", type=float, default=0.0)
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--lex", type=str, default="data/memory/lex_memory.json")

    ap.add_argument("--telemetry", type=str, default="data/telemetry/demo5_akg_consolidation.qdata.json")
    ap.add_argument("--plot", type=str, default="data/telemetry/demo5_edge_strengths.png")
    ap.add_argument("--graph", type=str, default="data/telemetry/demo5_akg_graph.json")

    ap.add_argument("--timeline", type=str, default="data/telemetry/demo5_akg_timeline.json")
    ap.add_argument("--emit-timeline", type=int, default=1, help="1=write timeline json")
    ap.add_argument("--topk", type=int, default=12)
    args = ap.parse_args()

    store = AKGTripletStore(alpha=args.alpha, half_life_s=args.half_life_s)

    triplets = _load_lexmemory_pairs(args.lex)
    if not triplets:
        triplets = [
            ("AION", "is", "alive"),
            ("AION", "learns_via", "CEE"),
            ("LexMemory", "reinforces", "AKG"),
            ("MeaningField", "vectorizes_to", "qphoto"),
            ("QQC", "feeds_back", "delta_ops"),
        ]

    session_id = f"DEMO5-{int(time.time())}"
    hits = 0

    timeline: List[Dict[str, Any]] = []
    last_strength: Dict[Triplet, float] = {}

    # do exactly N updates (clean + predictable)
    for i in range(max(1, int(args.rounds))):
        t = triplets[i % len(triplets)]
        e = store.reinforce(*t, hit=1.0)
        hits += 1

        if (i % 25) == 0:
            print(f"[{session_id}] reinforce {t} -> strength={e.strength:.3f} count={e.count}")

        if args.emit_timeline == 1:
            prev = last_strength.get(t, 0.0)
            last_strength[t] = float(e.strength)
            timeline.append({
                "i": i,
                "s": e.s, "r": e.r, "o": e.o,
                "strength": float(e.strength),
                "delta_strength": float(e.strength - prev),
                "count": int(e.count),
                "ts": float(e.last_ts),
            })

    store.save()

    top = store.top_edges(k=min(int(args.topk), len(store.edges) or 1))
    labels = [f"{e.s} {e.r} {e.o}" for e in top]
    strengths = [float(e.strength) for e in top]
    _plot_strengths(args.plot, labels, strengths)

    graph_path = export_akg_graph(store, args.graph)

    if args.emit_timeline == 1:
        os.makedirs(os.path.dirname(args.timeline), exist_ok=True)
        with open(args.timeline, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "session_id": session_id, "timeline": timeline}, f, ensure_ascii=False, indent=2)

    write_qdata(args.telemetry, {
        "demo": "demo5_akg_consolidation",
        "session_id": session_id,
        "alpha": args.alpha,
        "half_life_s": args.half_life_s,
        "rounds": int(args.rounds),
        "edges_total": len(store.edges),
        "reinforcements": hits,
        "top_edges": [{"s": e.s, "r": e.r, "o": e.o, "strength": e.strength, "count": e.count} for e in top],
        "artifacts": {
            "akg_store": store.path,
            "plot": args.plot,
            "graph": graph_path,
            "timeline": args.timeline if args.emit_timeline == 1 else None,
        },
    })

    print(f"[{session_id}] wrote {store.path}")
    print(f"[{session_id}] wrote {args.telemetry}")
    print(f"[{session_id}] wrote {args.plot}")
    print(f"[{session_id}] wrote {graph_path}")
    if args.emit_timeline == 1:
        print(f"[{session_id}] wrote {args.timeline}")

if __name__ == "__main__":
    main()