# backend/modules/beamline/beam_store.py
"""
BeamLine store: persist QWave beams + entanglements and provide simple queries.
Uses SQLAlchemy if DATABASE_URL is set; falls back to JSONL for dev.
No top-level imports from other project modules to avoid circulars.
"""
import os, json
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional

USE_SQLA = True
try:
    from sqlalchemy import Column, String, Float, Integer, JSON, create_engine, select
    from sqlalchemy.orm import declarative_base, sessionmaker
except Exception:
    USE_SQLA = False

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
RUNTIME_DIR = os.path.abspath("./runtime/beamline")
os.makedirs(RUNTIME_DIR, exist_ok=True)
JSONL_PATH = os.path.join(RUNTIME_DIR, "beam_events.jsonl")

if USE_SQLA:
    Base = declarative_base()

    class BeamEvent(Base):
        __tablename__ = "beam_events"
        id = Column(Integer, primary_key=True, autoincrement=True)
        beam_id = Column(String, index=True)
        cell_id = Column(String, index=True)
        sheet_run_id = Column(String, index=True)
        container_id = Column(String, index=True)
        eid = Column(String, index=True, nullable=True)
        stage = Column(String, index=True, nullable=True)
        token = Column(String, index=True, nullable=True)
        result = Column(JSON)
        timestamp = Column(String, index=True)

    class EntanglementLink(Base):
        __tablename__ = "entanglement_links"
        id = Column(Integer, primary_key=True, autoincrement=True)
        eid = Column(String, index=True)
        cell_id = Column(String, index=True)
        sheet_run_id = Column(String, index=True)
        container_id = Column(String, index=True)

    engine = create_engine(DATABASE_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def ensure_tables():
        Base.metadata.create_all(bind=engine)
else:
    def ensure_tables():
        # JSONL fallback has no schema
        pass

def _dt() -> str:
    return datetime.now(UTC).isoformat()

def persist_beam_events(cells: List[Any], context: Dict[str, Any]) -> None:
    """Persist all cell.wave_beams and the entanglement map in context."""
    ensure_tables()
    sheet_run_id = context.get("sheet_run_id")
    container_id = context.get("container_id")
    ent_map: Dict[str, set] = context.get("entanglements_map", {}) or {}

    if USE_SQLA:
        with SessionLocal() as s:
            # store events
            for cell in cells:
                beams = getattr(cell, "wave_beams", []) or []
                for b in beams:
                    eids = b.get("entanglement_ids") or [None]
                    for eid in eids:
                        evt = BeamEvent(
                            beam_id=b.get("beam_id"),
                            cell_id=getattr(cell, "id", ""),
                            sheet_run_id=sheet_run_id,
                            container_id=container_id,
                            eid=eid,
                            stage=b.get("stage"),
                            token=b.get("token"),
                            result=b.get("result"),
                            timestamp=b.get("timestamp") or _dt(),
                        )
                        s.add(evt)
            # store entanglement links
            for eid, members in ent_map.items():
                for cid in (members if isinstance(members, (set, list, tuple)) else [members]):
                    link = EntanglementLink(
                        eid=eid,
                        cell_id=cid,
                        sheet_run_id=sheet_run_id,
                        container_id=container_id,
                    )
                    s.add(link)
            s.commit()
    else:
        # JSONL fallback
        payload = {
            "sheet_run_id": sheet_run_id,
            "container_id": container_id,
            "timestamp": _dt(),
            "events": [],
            "entanglements": {k: sorted(list(v)) for k, v in ent_map.items()},
        }
        for cell in cells:
            for b in (getattr(cell, "wave_beams", []) or []):
                item = dict(b)
                item["cell_id"] = getattr(cell, "id", "")
                item["sheet_run_id"] = sheet_run_id
                item["container_id"] = container_id
                payload["events"].append(item)
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

def get_beams_for_eid(eid: str, limit: int = 100, container_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if USE_SQLA:
        with SessionLocal() as s:
            q = select(BeamEvent).where(BeamEvent.eid == eid)
            if container_id:
                q = q.where(BeamEvent.container_id == container_id)
            q = q.order_by(BeamEvent.id.desc()).limit(limit)
            rows = s.execute(q).scalars().all()
            return [dict(
                beam_id=r.beam_id, cell_id=r.cell_id, sheet_run_id=r.sheet_run_id,
                container_id=r.container_id, eid=r.eid, stage=r.stage, token=r.token,
                result=r.result, timestamp=r.timestamp
            ) for r in rows]
    else:
        # naive JSONL scan
        out = []
        try:
            with open(JSONL_PATH, "r", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    blob = json.loads(line)
                    if container_id and blob.get("container_id") != container_id:
                        continue
                    for e in blob.get("events", []):
                        eids = e.get("entanglement_ids") or []
                        if eid in eids:
                            out.append(e)
                            if len(out) >= limit:
                                return out
        except FileNotFoundError:
            pass
        return out

def get_lineage_for_cell(cell_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    if USE_SQLA:
        with SessionLocal() as s:
            q = select(BeamEvent).where(BeamEvent.cell_id == cell_id).order_by(BeamEvent.id.desc()).limit(limit)
            rows = s.execute(q).scalars().all()
            return [dict(
                beam_id=r.beam_id, cell_id=r.cell_id, sheet_run_id=r.sheet_run_id,
                container_id=r.container_id, eid=r.eid, stage=r.stage, token=r.token,
                result=r.result, timestamp=r.timestamp
            ) for r in rows]
    else:
        out = []
        try:
            with open(JSONL_PATH, "r", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    blob = json.loads(line)
                    for e in blob.get("events", []):
                        if e.get("cell_id") == cell_id:
                            out.append(e)
                            if len(out) >= limit:
                                return out
        except FileNotFoundError:
            pass
        return out

def get_sheet_lineage(sheet_run_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return events grouped by cell for a given sheet_run_id."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    if USE_SQLA:
        with SessionLocal() as s:
            q = select(BeamEvent).where(BeamEvent.sheet_run_id == sheet_run_id).order_by(BeamEvent.id.asc())
            rows = s.execute(q).scalars().all()
            for r in rows:
                grouped.setdefault(r.cell_id, []).append(dict(
                    beam_id=r.beam_id, cell_id=r.cell_id, sheet_run_id=r.sheet_run_id,
                    container_id=r.container_id, eid=r.eid, stage=r.stage, token=r.token,
                    result=r.result, timestamp=r.timestamp
                ))
            return grouped
    else:
        try:
            with open(JSONL_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    blob = json.loads(line)
                    if blob.get("sheet_run_id") != sheet_run_id:
                        continue
                    for e in blob.get("events", []):
                        cid = e.get("cell_id")
                        grouped.setdefault(cid, []).append(e)
        except FileNotFoundError:
            pass
        return grouped

def merge_entanglements(target_map: Dict[str, set], source_map: Dict[str, set]) -> Dict[str, set]:
    """Union merge two {eid -> set(cell_ids)} maps."""
    out = {k: set(v) for k, v in (target_map or {}).items()}
    for eid, members in (source_map or {}).items():
        out.setdefault(eid, set()).update(set(members))
    return out

def ghost_replay_for_eid(eid: str, limit: int = 10, container_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the last N events tied to an entanglement id (most recent first)."""
    return get_beams_for_eid(eid=eid, limit=limit, container_id=container_id)