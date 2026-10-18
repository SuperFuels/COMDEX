from __future__ import annotations

from backend.modules.aion_business.api import business_twin_data_api


def test_business_twin_uses_configured_repository_without_implicit_fallback(monkeypatch) -> None:
    selected = object()
    calls = []

    def choose():
        calls.append(True)
        return selected

    monkeypatch.setattr(
        business_twin_data_api,
        "configured_business_container_repository",
        choose,
    )
    assert business_twin_data_api._repo() is selected
    assert calls == [True]
