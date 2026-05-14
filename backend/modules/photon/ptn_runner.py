import importlib
from typing import Dict, Any

def _ensure_photon_importer() -> None:
    try:
        # canonical wrapper; safe if already installed
        from backend.modules.photonlang.runtime import photon_importer
        photon_importer.install()
    except Exception:
        # as a fallback, importing the core importer also auto-registers
        import backend.modules.photonlang.importer  # noqa: F401

def _bind_python_host_modules(host_imports: list[dict], ctx: Dict[str, Any]) -> None:
    """
    Import Python modules (including .photon/.pthon via importer) and bind them
    into the page execution context. Alias precedence:
      - explicit `as`
      - last dotted segment of module name
    """
    _ensure_photon_importer()
    py_ns = ctx.setdefault("python", {})  # optional namespacing
    for ent in host_imports:
        if ent["host"] != "python":
            continue
        module_name = ent["module"]
        mod = importlib.import_module(module_name)
        alias = ent.get("as") or module_name.rsplit(".", 1)[-1]
        # expose in two convenient places:
        ctx[alias] = mod          # direct alias (e.g., `demo.fn()`)
        py_ns[alias] = mod        # namespaced (e.g., `python['demo'].fn()`)

def run_ptn_page(page: dict, *, context: Dict[str, Any] | None = None) -> Any:
    """
    Your existing page runner entrypoint. Call after validation so `_host_imports`
    is present.
    """
    ctx = {} if context is None else dict(context)
    host_imports = page.get("_host_imports", [])
    _bind_python_host_modules(host_imports, ctx)

    # ... rest of your execution flow ...
    # e.g., compile Photon blocks, execute capsules with `ctx` available
    return _execute_page_blocks(page, ctx)  # whatever your current call is