# Makefile (at repo root)

.PHONY: all sync-docs docs test photon-tests codex-tests

PY := PYTHONPATH=.
# Default test target (can be overridden: make test TEST=path/to/tests)
TEST ?= backend/photon_algebra/tests

all: sync-docs photon-tests

sync-docs:
	@echo "🔧 Running doc sync…"
	@$(PY) python backend/tools/sync_docs.py

docs: sync-docs
	@echo "📦 Docs rebuilt at docs/"

# Scoped test runner (override TEST=… as needed)
test:
	@echo "🧪 Running pytest on $(TEST)…"
	@$(PY) pytest -q $(TEST)

# Convenience targets
photon-tests:
	@$(PY) pytest -q backend/photon_algebra/tests

codex-tests:
	@$(PY) pytest -q backend/modules/tests

benchmark:
	@echo "⚡ Running Photon benchmark..."
	@PYTHONPATH=. python backend/photon_algebra/benchmarks.py | tee -a docs/rfc/Photon_Benchmarks.md