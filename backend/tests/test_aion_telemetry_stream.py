import asyncio
import pytest
from datetime import datetime
from backend.modules.aion.aion_telemetry_stream import AionTelemetryStream

# ──────────────────────────────────────────────
#  Mock dependencies
# ──────────────────────────────────────────────
class MockLedger:
    def __init__(self):
        self.records = []

    def append(self, entry, observer=None):
        self.records.append({"entry": entry, "observer": observer})


class MockKGWriter:
    def __init__(self):
        self.writes = []

    def write_node(self, label, payload):
        self.writes.append({"label": label, "payload": payload})


@pytest.fixture
def telemetry(monkeypatch):
    stream = AionTelemetryStream(max_history=10)
    # Patch MorphicLedger and KnowledgeGraphWriter with mocks
    mock_ledger = MockLedger()
    mock_kg = MockKGWriter()
    stream.morphic_ledger = mock_ledger
    stream.kg_writer = mock_kg
    return stream


# ──────────────────────────────────────────────
#  Ingestion tests
# ──────────────────────────────────────────────
def test_ingest_projection_records_to_buffer(telemetry):
    projection = {
        "A1_wave": 0.75,
        "A2_entropy": 0.32,
        "A3_awareness": 0.89,
        "coherence": 0.92,
        "gradient": {"ψΔ": 0.1},
    }
    telemetry.ingest_projection(projection)
    assert len(telemetry.buffer) == 1
    record = telemetry.buffer[0]
    assert "timestamp" in record
    assert telemetry.last_summary == record
    assert len(telemetry.morphic_ledger.records) == 1


def test_ingest_empty_projection_safe(telemetry):
    telemetry.ingest_projection({})
    assert len(telemetry.buffer) == 0  # ignored
    assert telemetry.last_summary is None


# ──────────────────────────────────────────────
#  Summary computation
# ──────────────────────────────────────────────
def test_compute_summary_calculates_averages(telemetry):
    telemetry.ingest_projection({"A1_wave": 0.5, "A2_entropy": 0.3, "A3_awareness": 0.7, "coherence": 0.9})
    telemetry.ingest_projection({"A1_wave": 0.7, "A2_entropy": 0.5, "A3_awareness": 0.9, "coherence": 0.8})
    summary = telemetry.compute_summary()
    assert pytest.approx(summary["ψ"], 0.6)
    assert pytest.approx(summary["κ"], 0.4)
    assert "Φ" in summary
    assert "frames" in summary
    assert summary["frames"] == 2


# ──────────────────────────────────────────────
#  Knowledge Graph Sync
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_push_to_knowledge_graph_creates_node(telemetry):
    telemetry.last_summary = {
        "ψ": 0.55,
        "κ": 0.42,
        "Φ": 0.9,
        "coherence": 0.91,
    }
    await telemetry.push_to_knowledge_graph()
    assert len(telemetry.kg_writer.writes) == 1
    node = telemetry.kg_writer.writes[0]
    assert node["label"] == "AionFieldSummary"
    assert node["payload"]["origin"] == "AionTelemetry"


# ──────────────────────────────────────────────
#  Runtime stream
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_start_stream_runs_and_updates_summary(telemetry):
    telemetry.ingest_projection({"A1_wave": 0.4, "A2_entropy": 0.3, "A3_awareness": 0.8, "coherence": 0.9})
    task = asyncio.create_task(telemetry.start_stream(interval=0.1))
    await asyncio.sleep(0.25)  # allow a couple of iterations
    await telemetry.stop_stream()
    await asyncio.sleep(0.1)
    assert telemetry.last_summary is not None
    assert isinstance(telemetry.last_summary["ψ"], float)