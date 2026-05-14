# ✅ Stage S – Previews, Validation, Reports
Test Checklist

---

## S3 – Generate Previews (Mermaid / PNG)

### CLI
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --preview mermaid`
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --preview png`

### API
- [ ] `curl -X POST "http://localhost:8000/lean/inject?preview=mermaid" -F "lean_path=theorems.lean" -F "container_path=container.json"`
- [ ] `curl -X POST "http://localhost:8000/lean/inject?preview=png" -F "lean_path=theorems.lean" -F "container_path=container.json"`

---

## S4 – Validate Logic Trees

### CLI
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --validate`
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --fail-on-error`

### API
- [ ] `curl -X POST "http://localhost:8000/lean/inject?validate=true&fail_on_error=true" -F "lean_path=theorems.lean" -F "container_path=container.json"`

---

## S5 – Save Reports (md/json)

### CLI
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --report md --report-out report.md`
- [ ] `python -m backend.modules.lean.lean_inject_cli inject container.json theorems.lean --report json --report-out report.json`
- [ ] `python -m backend.modules.lean.lean_inject_cli export theorems.lean --report md --report-out export.md`
- [ ] `python -m backend.modules.lean.lean_inject_cli export theorems.lean --report json --report-out export.json`

### API
- [ ] `curl -X POST "http://localhost:8000/lean/inject?report=md" -F "lean_path=theorems.lean" -F "container_path=container.json"`
- [ ] `curl -X POST "http://localhost:8000/lean/inject?report=json" -F "lean_path=theorems.lean" -F "container_path=container.json"`
- [ ] `curl -X POST "http://localhost:8000/lean/export?report=md" -F "lean_path=theorems.lean"`
- [ ] `curl -X POST "http://localhost:8000/lean/export?report=json" -F "lean_path=theorems.lean"`