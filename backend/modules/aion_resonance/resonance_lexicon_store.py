from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


DEFAULT_BASE_LEXICON_PATH = Path(__file__).with_name("boot_config.json")


def _mapping(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): dict(payload)
        for key, payload in value.items()
        if isinstance(payload, dict)
    }


class ResonanceLexiconStore:
    """Read-only product lexicon plus business-owned learned overrides.

    The packaged boot lexicon is application content and is never mutated by
    this adapter.  Guardian mode stores learned terms and drift refinements in
    ``learning.customer_state``.  An explicit legacy path is available only
    for migration and isolated compatibility tests.
    """

    ENTITY_ID = "resonance_lexicon_overrides"

    def __init__(
        self,
        *,
        vault_store: AionLearningVaultStore | None = None,
        base_path: str | Path = DEFAULT_BASE_LEXICON_PATH,
        legacy_path: str | Path | None = None,
    ) -> None:
        self.base_path = Path(base_path)
        self.legacy_path = Path(legacy_path) if legacy_path is not None else None
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=legacy_path is None
        )

    def _read_json(self, path: Path) -> dict[str, dict[str, Any]]:
        if not path.is_file():
            return {}
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return {}

    def base(self) -> dict[str, dict[str, Any]]:
        return self._read_json(self.base_path)

    def overrides(self) -> dict[str, dict[str, Any]]:
        if self.vault_store.enabled:
            payload = self.vault_store.get_state(self.ENTITY_ID, {"overrides": {}})
            return _mapping(payload.get("overrides", {})) if isinstance(payload, dict) else {}
        if self.legacy_path is not None:
            return self._read_json(self.legacy_path)
        return {}

    def load(self) -> dict[str, dict[str, Any]]:
        merged = self.base()
        merged.update(self.overrides())
        return merged

    def put(self, term: str, signature: Mapping[str, Any]) -> dict[str, Any]:
        key = str(term).strip()
        if not key:
            raise ValueError("resonance_lexicon_term_required")
        overrides = self.overrides()
        overrides[key] = dict(signature)
        self.replace_overrides(overrides)
        return dict(overrides[key])

    def replace_overrides(self, overrides: Mapping[str, Any]) -> None:
        normalized = _mapping(dict(overrides))
        if self.vault_store.enabled:
            self.vault_store.put_state(
                self.ENTITY_ID,
                {
                    "overrides": normalized,
                    "base_lexicon_is_application_content": True,
                },
            )
            return
        if self.legacy_path is None:
            raise RuntimeError("resonance_lexicon_guardian_store_not_configured")
        self.legacy_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


RESONANCE_LEXICON = ResonanceLexiconStore()
