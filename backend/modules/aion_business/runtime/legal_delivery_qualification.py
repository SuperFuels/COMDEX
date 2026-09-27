"""Content-free qualification evidence for Legal signed-document delivery.

This module does not send mail and does not turn provider acceptance into a
delivery claim.  It evaluates the encrypted Legal delivery outbox after live or
test exercises have run and emits a bounded, content-free report describing
which provider-authenticated paths were actually observed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.aion_business.runtime.legal_delivery_service import (
    LegalDeliveryError,
    LegalDeliveryService,
)


class LegalDeliveryQualificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LegalDeliveryQualificationEvaluator:
    """Evaluate provider-authenticated delivery and recovery evidence.

    Reports intentionally exclude recipient addresses, subjects, message bodies,
    attachment names, provider request identifiers and provider trace identifiers.
    Identifiers retained for correlation are one-way commitments scoped to this
    report.
    """

    SCHEMA_VERSION = "tessaris.legal-delivery-qualification.v1"
    ENVIRONMENTS = {"test", "staging", "production"}
    PROVIDER_REQUIREMENTS = {
        "resend": (
            "delivered",
            "delayed_reauthorized_delivered",
            "bounced_reauthorized_delivered",
            "rejected_reauthorized_delivered",
        ),
        "microsoft_graph": (
            "delivered",
            "delayed_reauthorized_delivered",
            "failed_reauthorized_delivered",
        ),
    }
    MICROSOFT_REQUIRED_SCOPES = {
        "Mail.ReadWrite", "Mail.Send", "ExchangeMessageTrace.Read.All",
    }
    MAX_RECORDS = 2_000

    def __init__(self, delivery_service: LegalDeliveryService) -> None:
        self.delivery_service = delivery_service

    def evaluate(
        self,
        workspace_id: str,
        *,
        environment: str,
        provider_configuration: Mapping[str, Any] | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        environment = str(environment or "").strip().lower()
        if environment not in self.ENVIRONMENTS:
            raise LegalDeliveryQualificationError("delivery_qualification_environment_invalid")
        try:
            records = self.delivery_service._records(workspace_id)
        except LegalDeliveryError as exc:
            raise LegalDeliveryQualificationError(str(exc)) from exc
        if len(records) > self.MAX_RECORDS:
            raise LegalDeliveryQualificationError("delivery_qualification_record_limit_reached")

        observed: dict[str, dict[str, list[dict[str, str]]]] = {
            provider: {case: [] for case in requirements}
            for provider, requirements in self.PROVIDER_REQUIREMENTS.items()
        }
        invalid_event_chains = 0
        manual_only_deliveries = 0
        submitted_without_delivery = 0

        for record in records:
            provider = str(record.get("provider") or "")
            if provider not in observed:
                continue
            if not self.delivery_service.verify_event_chain(record):
                invalid_event_chains += 1
                continue
            status = str(record.get("status") or "")
            authoritative_delivered = self._authoritative_provider_outcome(
                provider, record, "delivered",
            )
            if status == "DELIVERED" and not authoritative_delivered:
                manual_only_deliveries += 1
                continue
            if status == "SUBMITTED_TO_PROVIDER":
                submitted_without_delivery += 1
            if status != "DELIVERED" or not authoritative_delivered:
                continue

            evidence = self._content_free_evidence(workspace_id, record)
            observed[provider]["delivered"].append(evidence)
            prior_statuses = {
                str(item.get("status") or "")
                for item in record.get("provider_history") or []
                if isinstance(item, Mapping)
            }
            event_types = [
                str(item.get("event_type") or "")
                for item in record.get("events") or []
                if isinstance(item, Mapping)
            ]
            if not self._ordered_retry_completed(event_types):
                continue
            if (
                "DELIVERY_DELAYED" in prior_statuses
                and self._authoritative_provider_outcome(provider, record, "delayed")
            ):
                observed[provider]["delayed_reauthorized_delivered"].append(evidence)
            if provider == "resend":
                if (
                    "BOUNCED" in prior_statuses
                    and self._authoritative_provider_outcome(provider, record, "bounced")
                ):
                    observed[provider]["bounced_reauthorized_delivered"].append(evidence)
                if (
                    "REJECTED" in prior_statuses
                    and self._authoritative_provider_outcome(provider, record, "rejected")
                ):
                    observed[provider]["rejected_reauthorized_delivered"].append(evidence)
            elif (
                "REJECTED" in prior_statuses
                and self._authoritative_provider_outcome(provider, record, "failed")
            ):
                observed[provider]["failed_reauthorized_delivered"].append(evidence)

        checks = self._configuration_checks(provider_configuration or {})
        coverage: dict[str, Any] = {}
        all_cases_pass = True
        for provider, requirements in self.PROVIDER_REQUIREMENTS.items():
            cases = {
                case: {
                    "passed": bool(observed[provider][case]),
                    "evidence": observed[provider][case],
                }
                for case in requirements
            }
            provider_passed = all(item["passed"] for item in cases.values())
            all_cases_pass = all_cases_pass and provider_passed
            coverage[provider] = {"passed": provider_passed, "cases": cases}

        integrity_passed = invalid_event_chains == 0
        configuration_passed = all(item["passed"] for item in checks.values())
        production_ready = (
            environment == "production"
            and all_cases_pass
            and integrity_passed
            and configuration_passed
        )
        if production_ready:
            result = "PRODUCTION_PROVIDER_CASES_PASSED"
        elif environment == "test" and all_cases_pass and integrity_passed:
            result = "LOCAL_QUALIFICATION_LOGIC_PASSED"
        else:
            result = "INCOMPLETE"

        report: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": generated_at or _now_iso(),
            "environment": environment,
            "workspace_commitment": sha256(workspace_id.encode("utf-8")).hexdigest(),
            "content_free": True,
            "claim_boundary": (
                "Provider submission is not delivery. This report records local "
                "observation of authenticated provider evidence and is not an "
                "independent provider attestation or legal-validity opinion."
            ),
            "provider_semantics": {
                "resend": (
                    "Authenticated webhook events distinguish delay, bounce, "
                    "provider rejection and delivery."
                ),
                "microsoft_graph": (
                    "Exact Internet Message-ID and recipient Message Trace distinguishes "
                    "delivery, delay/quarantine and failed delivery; the high-level trace "
                    "does not independently distinguish bounce from another failure."
                ),
            },
            "configuration_checks": checks,
            "coverage": coverage,
            "integrity": {
                "event_chains_valid": integrity_passed,
                "invalid_event_chain_count": invalid_event_chains,
                "manual_only_delivery_count": manual_only_deliveries,
                "submitted_without_delivery_count": submitted_without_delivery,
                "evaluated_record_count": len(records),
            },
            "production_ready": production_ready,
            "result": result,
        }
        report["report_sha256"] = sha256(_canonical(report)).hexdigest()
        return report

    def write_report(self, output: str | Path, report: Mapping[str, Any]) -> Path:
        path = Path(output).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = Path(os.path.abspath(path))
        if path.suffix.lower() != ".json":
            raise LegalDeliveryQualificationError("delivery_qualification_report_must_be_json")
        for component in (path, *path.parents):
            if component.is_symlink():
                raise LegalDeliveryQualificationError("delivery_qualification_report_symlink_refused")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise LegalDeliveryQualificationError("delivery_qualification_report_already_exists")
        payload = json.dumps(dict(report), indent=2, sort_keys=True) + "\n"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                path.unlink(missing_ok=True)
            finally:
                raise
        return path

    @classmethod
    def verify_report(cls, report: Mapping[str, Any]) -> bool:
        value = dict(report)
        supplied = str(value.pop("report_sha256", ""))
        expected = sha256(_canonical(value)).hexdigest()
        return bool(supplied) and hmac.compare_digest(supplied, expected)

    @staticmethod
    def _ordered_retry_completed(event_types: Sequence[str]) -> bool:
        try:
            retry = event_types.index("DELIVERY_RETRY_AUTHORIZED")
            submitted = event_types.index("DELIVERY_SUBMITTED_TO_PROVIDER", retry + 1)
            event_types.index("DELIVERY_DELIVERED", submitted + 1)
            return True
        except ValueError:
            return False

    @staticmethod
    def _authoritative_provider_outcome(
        provider: str, record: Mapping[str, Any], outcome: str,
    ) -> bool:
        events = [
            item for item in record.get("provider_events") or []
            if isinstance(item, Mapping)
        ]
        if provider == "resend":
            accepted = {
                "delivered": {"email.delivered"},
                "delayed": {"email.delivery_delayed"},
                "bounced": {"email.bounced"},
                "rejected": {"email.failed", "email.suppressed"},
            }.get(outcome, set())
            return any(str(item.get("event_type") or "") in accepted for item in events)
        if provider == "microsoft_graph":
            accepted = {
                "delivered": {"delivered"},
                "delayed": {"quarantined", "filteredasspam"},
                "failed": {"failed"},
            }.get(outcome, set())
            return any(
                item.get("event_type") == "microsoft_graph.message_trace"
                and str(item.get("provider_status") or "").lower() in accepted
                for item in events
            )
        return False

    @staticmethod
    def _content_free_evidence(
        workspace_id: str, record: Mapping[str, Any],
    ) -> dict[str, str]:
        delivery_id = str(record.get("delivery_id") or "")
        events = list(record.get("events") or [])
        provider_events = list(record.get("provider_events") or [])
        scope = f"{workspace_id}:{delivery_id}".encode("utf-8")
        return {
            "delivery_commitment": sha256(scope).hexdigest(),
            "attachment_sha256": str(record.get("attachment_sha256") or ""),
            "last_event_hash": str(events[-1].get("event_hash") or "") if events else "",
            "provider_event_set_sha256": sha256(_canonical(provider_events)).hexdigest(),
        }

    @classmethod
    def _configuration_checks(cls, value: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        resend = value.get("resend") if isinstance(value.get("resend"), Mapping) else {}
        microsoft = (
            value.get("microsoft_graph")
            if isinstance(value.get("microsoft_graph"), Mapping) else {}
        )
        callback_url = str(resend.get("callback_url") or "").strip()
        resend_passed = (
            callback_url.startswith("https://")
            and bool(resend.get("vault_connected"))
            and bool(resend.get("signing_secret_registered"))
        )
        scopes = {
            str(item).strip() for item in microsoft.get("granted_scopes") or []
            if str(item).strip()
        }
        microsoft_passed = (
            bool(microsoft.get("vault_connected"))
            and bool(microsoft.get("message_trace_service_principal_provisioned"))
            and cls.MICROSOFT_REQUIRED_SCOPES.issubset(scopes)
        )
        return {
            "resend": {
                "passed": resend_passed,
                "https_callback_registered": callback_url.startswith("https://"),
                "vault_connected": bool(resend.get("vault_connected")),
                "signing_secret_registered": bool(resend.get("signing_secret_registered")),
                "source": "operator_supplied_configuration_inventory",
            },
            "microsoft_graph": {
                "passed": microsoft_passed,
                "vault_connected": bool(microsoft.get("vault_connected")),
                "required_scopes_present": sorted(cls.MICROSOFT_REQUIRED_SCOPES.intersection(scopes)),
                "missing_scopes": sorted(cls.MICROSOFT_REQUIRED_SCOPES.difference(scopes)),
                "message_trace_service_principal_provisioned": bool(
                    microsoft.get("message_trace_service_principal_provisioned")
                ),
                "source": "operator_supplied_configuration_inventory",
            },
        }
