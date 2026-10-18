from __future__ import annotations

from backend.modules.aion_business.runtime import sales_revenue_service


def test_sales_projection_repository_uses_explicit_authority_selector(monkeypatch) -> None:
    selected = object()
    monkeypatch.setattr(
        sales_revenue_service,
        "configured_business_container_repository",
        lambda: selected,
    )
    monkeypatch.setattr(
        sales_revenue_service,
        "OrganizationAuthorityService",
        lambda repository: ("authority", repository),
    )
    service = sales_revenue_service.SalesRevenueService()
    assert service.repository is selected
    assert service.authority == ("authority", selected)
