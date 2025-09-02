def trace_log_if_available(data, context: str = "unspecified"):
    """
    Optionally logs symbolic trace data from synthesis/prediction tools.
    Prints to console for now; could be extended to file or GHX overlay.

    Args:
        data (Any): The result object to log.
        context (str): Source of the trace (e.g., 'creative_cli', 'prediction_engine').
    """
    try:
        import json
        print(f"\n[TRACE] [{context}] Symbolic Trace Output:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[TRACE WARNING] Could not log trace output: {e}")