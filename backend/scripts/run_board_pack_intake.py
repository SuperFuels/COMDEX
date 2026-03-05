# /workspaces/COMDEX/backend/scripts/run_board_pack_intake.py
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

# --- AION Equities modules ---
from backend.modules.aion_equities.assessment_runtime import AssessmentRuntime
from backend.modules.aion_equities.assessment_store import AssessmentStore
from backend.modules.aion_equities.company_intelligence_snapshot_loader import (
    CompanyIntelligenceSnapshotLoader,
)
from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.document_ingestion_runtime import DocumentIngestionRuntime
from backend.modules.aion_equities.openai_company_profile_mapper import OpenAICompanyProfileMapper
from backend.modules.aion_equities.openai_document_analysis_runtime import OpenAIDocumentAnalysisRuntime
from backend.modules.aion_equities.openai_document_intake_runtime import OpenAIDocumentIntakeRuntime
from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.quarter_event_store import QuarterEventStore
from backend.modules.aion_equities.reference_maintenance_runtime import ReferenceMaintenanceRuntime
from backend.modules.aion_equities.source_document_store import SourceDocumentStore
from backend.modules.aion_equities.thesis_runtime import ThesisRuntime
from backend.modules.aion_equities.thesis_store import ThesisStore
from backend.modules.aion_equities.variable_watch_store import VariableWatchStore


# -----------------------------
# tiny .env loader (no deps)
# -----------------------------
def load_env_file(path: Path) -> bool:
    """
    Minimal .env parser:
      KEY=VALUE
      ignores blank lines and lines starting with '#'
    Does NOT override env vars already set.
    """
    if not path.exists() or not path.is_file():
        return False

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if not key:
            continue
        if os.getenv(key) is None:
            os.environ[key] = val
    return True


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# -----------------------------
# PDF text extraction helpers
# -----------------------------
def _pdftotext_available() -> bool:
    try:
        subprocess.run(["pdftotext", "-v"], capture_output=True, check=False)
        return True
    except Exception:
        return False


def extract_pdf_to_text(pdf_path: Path, out_txt: Path) -> None:
    """
    Extract PDF text to out_txt.

    Preference order:
      1) pdftotext -layout (if installed)
      2) pdfminer.six (if installed)
      3) pypdf (if installed)

    If none available, raise with actionable guidance.
    """
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    if _pdftotext_available():
        subprocess.run(["pdftotext", "-layout", str(pdf_path), str(out_txt)], check=True)
        return

    # pdfminer.six fallback
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text  # type: ignore

        text = pdfminer_extract_text(str(pdf_path)) or ""
        _write_text(out_txt, text)
        return
    except Exception:
        pass

    # pypdf fallback
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        _write_text(out_txt, text)
        return
    except Exception as e:
        raise RuntimeError(
            "No PDF extractor available.\n"
            "Install one of:\n"
            "  - `pdftotext` (poppler-utils)\n"
            "  - `pdfminer.six`\n"
            "  - `pypdf`\n"
            "Or run with --text-file <already_extracted.txt> to skip PDF extraction."
        ) from e


# -----------------------------
# OpenAI client wrapper
# -----------------------------
def load_openai_client_from_env() -> Any:
    """
    Minimal OpenAI client wrapper.

    Compatibility goals:
      - Works across older/newer OpenAI python SDKs.
      - Prefers JSON-only outputs.
      - Avoids passing `response_format` to Responses API (some installs reject it).
      - Uses Chat Completions JSON response_format when available.

    Supports multi-packet types:
      - packet_type=openai_document_analysis (Phase-1)
      - packet_type=openai_variable_watch_phase2 (Phase-2)
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing OPENAI_API_KEY in environment.\n"
            "Add it to /workspaces/COMDEX/.env.local as:\n"
            "  OPENAI_API_KEY=sk-...\n"
            "Optionally set:\n"
            "  OPENAI_MODEL=gpt-4.1-mini\n"
        )

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "openai python SDK not installed.\n"
            "Install it in your environment or replace load_openai_client_from_env() "
            "with your existing OpenAI wrapper."
        ) from e

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()

    def _strip_fences(t: str) -> str:
        s = (t or "").strip()
        if not s:
            return ""
        s = re.sub(r"^\s*```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
        return s.strip()

    def _force_json_from_text(text: str, *, packet_type: str = "") -> Dict[str, Any]:
        """
        Robust parsing:
          - handles fenced blocks
          - handles top-level arrays (wrap arrays for phase-2 into {"variables":[...]})
          - attempts best-effort extraction of the largest {...} or [...] span

        NOTE:
          - Always returns a dict (non-dict parses are wrapped).
        """
        t = _strip_fences(text)
        if not t:
            return {}

        # 1) direct parse (dict or list)
        try:
            obj = json.loads(t)
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list):
                if packet_type == "openai_variable_watch_phase2":
                    return {"variables": obj}
                return {"items": obj}
        except Exception:
            pass

        # 2) best-effort extraction of JSON spans
        candidates: list[str] = []

        first_obj = t.find("{")
        last_obj = t.rfind("}")
        if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
            candidates.append(t[first_obj : last_obj + 1])

        first_arr = t.find("[")
        last_arr = t.rfind("]")
        if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
            candidates.append(t[first_arr : last_arr + 1])

        for c in candidates:
            try:
                obj = json.loads(c)
                if isinstance(obj, dict):
                    return obj
                if isinstance(obj, list):
                    if packet_type == "openai_variable_watch_phase2":
                        return {"variables": obj}
                    return {"items": obj}
            except Exception:
                continue

        return {"raw_text": t}

    def _build_prompt(packet: Dict[str, Any]) -> str:
        packet_type = str(packet.get("packet_type") or "").strip()

        if packet_type == "openai_variable_watch_phase2":
            return (
                "SYSTEM:\n"
                "You convert company document analysis into machine-trackable monitoring variables.\n"
                "Return ONLY valid JSON. No markdown. No commentary.\n\n"
                "CRITICAL RULES (MUST FOLLOW):\n"
                "- Use ONLY the packet context to populate values.\n"
                "- DO NOT copy placeholder/example values.\n"
                "- Output MUST be a JSON object with key: variables (array).\n"
                "- Return 5–10 variables.\n"
                "- For EVERY variable, these fields MUST be NON-NULL and NON-EMPTY strings:\n"
                "  name, why_it_matters, data_source, feed_id, unit,\n"
                "  threshold_early, threshold_confirm, threshold_break,\n"
                "  thesis_action_on_confirm, thesis_action_on_break.\n"
                "- current_value may be null ONLY if not found in packet document_text.\n"
                "- lag_weeks MUST be an integer >= 0.\n"
                "- direction MUST be exactly: \"positive\" or \"negative\".\n"
                "- impact_weight MUST be a number between 0.05 and 0.30.\n"
                "- thresholds MUST contain numeric comparisons AND a time window.\n"
                "  Examples of VALID thresholds:\n"
                "    \"USG >= 4.0 for 1 quarter\"\n"
                "    \"UOM >= 19.5 for 2 consecutive quarters\"\n"
                "    \"FX(EUR/BRL) <= 5.8 for 6 weeks\"\n"
                "  INVALID thresholds:\n"
                "    \"improving\", \"better\", \"stable\", \"watch closely\".\n"
                "- feed_id MUST be snake_case and UNIQUE across variables.\n"
                "- Order variables by impact_weight DESC.\n"
                "- Total impact_weight across all variables should sum to ~1.0 (0.8–1.2 acceptable).\n\n"
                "OUTPUT SHAPE (EXACT):\n"
                "{\n"
                '  "variables": [\n'
                "    {\n"
                '      "name": "...",\n'
                '      "why_it_matters": "...",\n'
                '      "data_source": "...",\n'
                '      "feed_id": "...",\n'
                '      "current_value": 0.0,\n'
                '      "unit": "...",\n'
                '      "lag_weeks": 0,\n'
                '      "direction": "positive",\n'
                '      "impact_weight": 0.10,\n'
                '      "threshold_early": "...",\n'
                '      "threshold_confirm": "...",\n'
                '      "threshold_break": "...",\n'
                '      "thesis_action_on_confirm": "...",\n'
                '      "thesis_action_on_break": "..."\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                f"PACKET:\n{json.dumps(packet, ensure_ascii=False)}"
            )

        return (
            "You are an analyst system. You will receive a JSON packet describing a company document.\n"
            "Return ONLY valid JSON matching this high-level shape:\n"
            "{company_profile:{...}, quarter_summary:{...}, trigger_map:{triggers:[...]}, "
            "feed_candidates:{feeds:[...]}, assessment_seed:{...}, thesis_seed:{...}, "
            "variable_watch_seed:{...}, quarter_event:{...}}\n"
            "Do not include markdown.\n\n"
            f"PACKET:\n{json.dumps(packet, ensure_ascii=False)}"
        )

    def _call(packet: Dict[str, Any]) -> Dict[str, Any]:
        packet_type = str(packet.get("packet_type") or "").strip()
        prompt = _build_prompt(packet)

        # 1) Try Responses API (no response_format for max compatibility)
        try:
            resp = client.responses.create(model=model, input=prompt)
            text = getattr(resp, "output_text", None)
            if isinstance(text, str) and text.strip():
                return _force_json_from_text(text, packet_type=packet_type)
        except Exception:
            pass

        # 2) Fallback: Chat Completions with JSON mode (commonly supported)
        try:
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON. No markdown."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = chat.choices[0].message.content or ""
            return _force_json_from_text(content, packet_type=packet_type)
        except Exception as e:
            raise RuntimeError(f"OpenAI call failed: {e}") from e

    return _call


def main() -> None:
    ap = argparse.ArgumentParser(description="Run AION Equities board-pack intake end-to-end.")
    ap.add_argument("--pdf", required=True, help="Path to PDF board pack / report")
    ap.add_argument("--company-ref", required=True, help="e.g. company/ULVR.L")
    ap.add_argument("--fiscal-period", required=True, help="e.g. 2026-Q4")
    ap.add_argument("--source-type", default="board_pack", help="board_pack | quarterly_report | trading_update ...")
    ap.add_argument("--base-dir", default="/workspaces/COMDEX/.runtime/equities", help="Runtime base dir for stores")
    ap.add_argument("--brief-id", default="brief/aion_equities_default", help="Operating brief id")
    ap.add_argument("--brief-version", default=None, help="Operating brief version lock (optional)")
    ap.add_argument("--document-type", default="board_pack", help="document_type passed to OpenAI runtime")
    ap.add_argument("--thesis-ref", default=None, help="Optional thesis ref")
    ap.add_argument("--no-autoload", action="store_true", help="Disable autoload text from parsed_text_ref")
    ap.add_argument("--text-file", default=None, help="Path to already-extracted text to skip PDF extraction")
    ap.add_argument("--dump-json", action="store_true", help="Dump full intake JSON to stdout")

    ap.add_argument(
        "--disable-phase2",
        action="store_true",
        help="Disable Phase-2 variable specification call (structured variable objects).",
    )
    ap.add_argument(
        "--phase2-text-max-chars",
        type=int,
        default=int(os.getenv("AION_PHASE2_TEXT_MAX_CHARS", "14000")),
        help="Max chars of document text to pass into Phase-2 variable spec packet.",
    )

    # Debug knobs (helps you see why nulls happen)
    ap.add_argument(
        "--dump-phase2-response",
        action="store_true",
        help="Print the raw Phase-2 response (best-effort) if available in intake output.",
    )

    args = ap.parse_args()

    repo_root = Path("/workspaces/COMDEX")
    env_path = repo_root / ".env.local"
    loaded = load_env_file(env_path)
    if loaded:
        print(f"✅ Loaded environment file: {env_path}")
    else:
        print(f"⚠️ No env file loaded at {env_path} (continuing with process env).")

    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    base_dir = Path(args.base_dir).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1) Get document text
    parsed_dir = base_dir / "parsed_text"
    parsed_txt = parsed_dir / f"{args.company_ref.replace('/', '_')}_{args.fiscal_period}.txt"

    if args.text_file:
        tf = Path(args.text_file).expanduser().resolve()
        if not tf.exists():
            raise FileNotFoundError(f"--text-file not found: {tf}")
        _write_text(parsed_txt, _read_text(tf))
    else:
        extract_pdf_to_text(pdf_path, parsed_txt)

    # 2) Setup stores
    brief_store = OpenAIOperatingBriefStore(base_dir=base_dir)
    seed_store = PilotCompanySeedStore(base_dir=base_dir)
    source_store = SourceDocumentStore(base_dir)
    qe_store = QuarterEventStore(base_dir=base_dir)
    tm_store = CompanyTriggerMapStore(base_dir=base_dir)
    vw_store = VariableWatchStore(base_dir=base_dir)
    assessment_store = AssessmentStore(base_dir=base_dir)
    thesis_store = ThesisStore(base_dir=base_dir)

    # Ensure an active brief exists; ensure brief_text is present (backfill if needed).
    try:
        brief_store.load_active_brief()
    except Exception:
        saved = brief_store.save_operating_brief(
            brief_id=args.brief_id,
            version="v1",
            title="AION Equities",
            summary="Default operating brief (auto-created by run script)",
            brief_text="Analyze company documents, extract structured intelligence, and return JSON.",
        )
        brief_store.set_active_brief(saved["brief_id"])

    # If brief_text is missing/empty, try to backfill it from sections (if method exists)
    try:
        active = brief_store.load_active_brief()
        brief_text_len = len((active.get("brief_text") or "").strip())
        if brief_text_len == 0 and hasattr(brief_store, "backfill_brief_text"):
            brief_store.backfill_brief_text(active.get("brief_id"))
    except Exception:
        pass

    # Ensure company seed exists; if not, create a minimal seed
    try:
        seed_store.load_company_seed(args.company_ref)
    except Exception:
        ticker = args.company_ref.split("/")[-1]
        seed_store.save_company_seed(
            company_ref=args.company_ref,
            company_id=args.company_ref,
            ticker=ticker,
            name=ticker,
            sector="unknown",
            country="unknown",
            predictability_profile={"acs_band": "medium", "sector_confidence_tier": "tier_2"},
        )

    # 3) Register source doc
    ingestion = DocumentIngestionRuntime(
        source_document_store=source_store,
        trigger_map_store=tm_store,
    )

    ingest_out = ingestion.ingest_document(
        company_ref=args.company_ref,
        source_type=args.source_type,
        fiscal_period_ref=args.fiscal_period,
        source_file_ref=str(pdf_path),
        parsed_text_ref=str(parsed_txt),
        tables_ref=None,
        provenance_hash=None,
    )
    document_id = ingest_out["source_document"]["document_id"]

    # 4) Build runtimes
    openai_client = load_openai_client_from_env()

    analysis_runtime = OpenAIDocumentAnalysisRuntime(
        operating_brief_store=brief_store,
        openai_client=openai_client,
        enable_phase2_variable_spec=(not args.disable_phase2),
        phase2_document_text_max_chars=int(args.phase2_text_max_chars),
    )

    mapper = OpenAICompanyProfileMapper()
    assessment_runtime = AssessmentRuntime(pilot_company_seed_store=seed_store, quarter_event_store=qe_store)
    thesis_runtime = ThesisRuntime(pilot_company_seed_store=seed_store)
    ref_runtime = ReferenceMaintenanceRuntime(pilot_company_seed_store=seed_store)

    intake = OpenAIDocumentIntakeRuntime(
        document_analysis_runtime=analysis_runtime,
        company_profile_mapper=mapper,
        quarter_event_store=qe_store,
        company_trigger_map_store=tm_store,
        variable_watch_store=vw_store,
        assessment_runtime=assessment_runtime,
        assessment_store=assessment_store,
        thesis_runtime=thesis_runtime,
        thesis_store=thesis_store,
        reference_maintenance_runtime=ref_runtime,
        source_document_store=source_store,
        document_text_base_dir=base_dir,
    )

    # 5) Run intake
    intake_out = intake.run_document_intake(
        company_ref=args.company_ref,
        document_ref=document_id,
        document_text="" if not args.no_autoload else _read_text(parsed_txt),
        document_type=args.document_type,
        thesis_ref=args.thesis_ref,
        operating_brief_id=args.brief_id,
        operating_brief_version=args.brief_version,
        autoload_document_text=not args.no_autoload,
        fiscal_period_ref=args.fiscal_period,
    )

    # 6) Load snapshot for quick sanity
    loader = CompanyIntelligenceSnapshotLoader(
        pilot_company_seed_store=seed_store,
        assessment_store=assessment_store,
        thesis_store=thesis_store,
        quarter_event_store=qe_store,
        trigger_map_store=tm_store,
        variable_watch_store=vw_store,
    )
    snap = loader.load_snapshot(company_ref=args.company_ref)

    print("\n=== INTAKE COMPLETE ===")
    print("company_ref:", args.company_ref)
    print("fiscal_period:", args.fiscal_period)
    print("source_document_id:", document_id)
    print("parsed_text_ref:", str(parsed_txt))
    print("resolved_document_text_len:", intake_out["persisted_objects"].get("resolved_document_text_len"))
    print("quarter_event_ref:", intake_out["persisted_objects"].get("quarter_event_ref"))
    print("trigger_map_ref:", intake_out["persisted_objects"].get("trigger_map_ref"))
    print("variable_watch_ref:", intake_out["persisted_objects"].get("variable_watch_ref"))
    print("assessment_ref:", intake_out["persisted_objects"].get("assessment_ref"))
    print("thesis_ref:", intake_out["persisted_objects"].get("thesis_ref"))

    cp = (intake_out.get("mapped_objects") or {}).get("company_profile", {})
    qs = (intake_out.get("mapped_objects") or {}).get("quarter_summary", {})
    print("\n--- SUMMARY ---")
    print("company_profile.name:", cp.get("name"))
    print("company_profile.sector:", cp.get("sector"))
    print("quarter_summary.headline:", qs.get("headline"))
    print("quarter_summary.summary:", qs.get("summary"))

    if args.dump_phase2_response:
        extra = (intake_out.get("normalized_analysis") or {}).get("_extra") or {}
        phase2 = extra.get("phase2_variable_watch_response")
        if phase2 is not None:
            print("\n--- PHASE-2 RAW RESPONSE (best-effort) ---")
            print(json.dumps(phase2, ensure_ascii=False, indent=2))
        else:
            print("\n--- PHASE-2 RAW RESPONSE ---")
            print("not present (phase-2 may be disabled, failed, or not stored).")

    if args.dump_json:
        print("\n--- FULL INTAKE JSON ---")
        print(json.dumps(intake_out, ensure_ascii=False, indent=2))

    print("\n--- SNAPSHOT KEYS ---")
    print("snapshot.company_ref:", snap.get("company_ref"))
    print("snapshot.has_assessment:", bool(snap.get("assessment")))
    print("snapshot.thesis_count:", len(snap.get("theses") or []))
    print("snapshot.has_trigger_map:", bool(snap.get("trigger_map")))
    print("snapshot.has_variable_watch:", bool(snap.get("variable_watch")))
    print()


if __name__ == "__main__":
    main()