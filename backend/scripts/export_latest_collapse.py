from backend.modules.collapse.collapse_trace_exporter import get_recent_collapse_traces, export_collapse_trace

traces = get_recent_collapse_traces(limit=1)
if not traces:
    print("❌ No collapse traces found.")
else:
    trace = traces[0]
    print(f"✅ Most recent trace: {trace.get('path')}")

    # If the trace has wave_state, re-export with qwave info
    wave_state = trace.get("wave_state")
    if wave_state:
        print("🔁 Re-exporting trace with QWave info...")
        export_collapse_trace(state=wave_state)
    else:
        print("⚠️ No wave_state found in trace. Nothing to export.")