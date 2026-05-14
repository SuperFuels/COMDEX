from .ptn_spec import normalize_host_import

_ALLOWED_HOSTS = {"python"}  # extend later if needed

def _validate_host_imports(page: dict) -> list[dict]:
    raw = page.get("imports") or []
    if not isinstance(raw, list):
        raise ValueError("`imports` must be a list")
    out: list[dict] = []
    for i, item in enumerate(raw):
        norm = normalize_host_import(item)
        if not norm:
            raise ValueError(f"imports[{i}] is not a valid host import")
        if norm["host"] not in _ALLOWED_HOSTS:
            raise ValueError(f"imports[{i}]: host '{norm['host']}' not allowed")
        # minimal module sanity
        if not norm["module"] or ".." in norm["module"]:
            raise ValueError(f"imports[{i}]: invalid module path")
        out.append(norm)
    return out

def validate_page(page: dict) -> dict:
    # ... your existing validation ...
    page["_host_imports"] = _validate_host_imports(page)
    return page