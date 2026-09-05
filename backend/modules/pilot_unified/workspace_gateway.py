from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity

from .compatibility import adapt_workspace
from .contracts import Invitation, InvitationState, Membership, SpaceRef, SurfaceManifest
from .pairing import MobilePairingAuthority


class AionBoardroomWorkspaceProvider:
    """Read-only mobile projection over the existing AION Business repositories."""

    provider_id = "aion-boardroom"

    def __init__(
        self,
        workspace_repository: Any,
        container_repository: Any,
        department_repository: Any,
        finance_conversation_service: Any | None = None,
        file_repository: Any | None = None,
    ) -> None:
        self.workspaces = workspace_repository
        self.containers = container_repository
        self.departments = department_repository
        self.finance_conversations = finance_conversation_service
        self.files = file_repository

    def list_workspaces(self) -> Sequence[Mapping[str, Any]]:
        return [self.workspaces.load(item).model_dump(mode="json") for item in self.workspaces.list_ids()]

    def describe_workspace(self, workspace_ref: str) -> Mapping[str, Any]:
        workspace = self.workspaces.load(workspace_ref)
        boardroom = self.containers.load_optional_dict(workspace_ref, "boardroom_snapshot") or {}
        payload = dict(boardroom.get("boardroom") or {})
        departments = [
            {"id": str(item.get("id") or item.get("department_id") or ""), "label": str(item.get("name") or item.get("label") or item.get("id") or "")}
            for item in payload.get("departments", []) if isinstance(item, Mapping)
        ]
        return {
            "id": workspace_ref,
            "departments": [item for item in departments if item["id"] and item["label"]][:100],
            "agents": [], "dashboards": [{"id": "boardroom", "label": "Boardroom overview"}],
            "files": self._file_catalog(workspace_ref), "packages": [], "decisions": [],
            "permitted_actions": ["workspace.read", "workspace.briefings.read", "workspace.dashboards.read", "workspace.departments.read"],
        }

    def read_surface(self, workspace_ref: str, surface: str, *, persona_id: str) -> Mapping[str, Any]:
        runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
        boardroom = self.containers.load_optional_dict(workspace_ref, "boardroom_snapshot") or {}
        runtime_summary = dict(runtime.get("runtime_summary") or {})
        dashboard = dict(runtime.get("dashboard_summary") or {})
        boardroom_summary = dict(runtime_summary.get("boardroom_summary") or {})
        boardroom_payload = dict(boardroom.get("boardroom") or {})
        if surface in {"overview", "briefings"}:
            source = boardroom_summary or {
                "pulse": boardroom_payload.get("pulse", {}),
                "center": boardroom_payload.get("center", {}),
                "departments": boardroom_payload.get("departments", []),
            }
        elif surface == "dashboards":
            source = dashboard
        elif surface == "departments":
            source = {
                "departments": boardroom_payload.get("departments", []),
                "work": [self._work_summary(item) for item in self.departments.list_for_workspace(workspace_ref)[:50]],
            }
        elif surface == "files":
            source = {"files": self._file_catalog(workspace_ref)}
        else:
            source = {}
        return {
            "revision": int((runtime.get("meta") or {}).get("revision") or 1),
            "data": self._mobile_summary(source),
        }

    def conversation_turn(
        self,
        workspace_ref: str,
        department_id: str,
        user_text: str,
        *,
        persona_id: str,
    ) -> Mapping[str, Any]:
        """Adapt existing read-only departmental conversation authorities.

        Finance has a permanent evidence-grounded conversation service. Other
        departments currently expose governed work queues, so their mobile turn is
        deliberately a deterministic briefing rather than an invented model answer.
        """
        question = " ".join(str(user_text or "").split())[:2_000]
        department = " ".join(str(department_id or "boardroom").split()).casefold()[:80]
        if not question:
            raise ValueError("workspace conversation text is required")
        if department == "finance" and self.finance_conversations is not None:
            result = dict(self.finance_conversations.answer(workspace_ref, question))
            turn = dict(result.get("turn") or {})
            return {
                "conversation_id": f"finance-terminal-{workspace_ref}",
                "department_id": "finance",
                "turn": turn,
                "provider": turn.get("provider", {}),
                "evidence": turn.get("sources", []),
                "reliability": turn.get("reliability", "unknown"),
                "external_writes_performed": False,
                "approval_gated": True,
            }

        surface = self.read_surface(workspace_ref, "departments", persona_id=persona_id)
        data = dict(surface.get("data") or {})
        relevant = [
            item for item in data.get("work", [])
            if isinstance(item, Mapping) and (
                department == "boardroom" or str(item.get("department_id") or "").casefold() == department
            )
        ][:12]
        if relevant:
            lines = "; ".join(
                f"{str(item.get('title') or 'Untitled work')[:120]} ({str(item.get('status') or 'unknown')})"
                for item in relevant
            )
            answer = f"Current {department.title()} work: {lines}. No external action was taken."
            reliability = "workspace_record_backed"
        else:
            answer = (
                f"I do not have enough recorded {department.title()} work evidence to answer that "
                "reliably. No external action was taken."
            )
            reliability = "insufficient_evidence"
        return {
            "conversation_id": f"mobile-{department}-{workspace_ref}",
            "department_id": department,
            "turn": {
                "turn_id": f"mobile-turn-{uuid4().hex}",
                "role": "assistant",
                "content": answer,
                "created_at": utc_now_iso(),
            },
            "provider": {"provider": "deterministic_workspace_projection", "model": None},
            "evidence": relevant,
            "reliability": reliability,
            "external_writes_performed": False,
            "approval_gated": True,
        }

    @staticmethod
    def _work_summary(envelope: Any) -> dict[str, Any]:
        task = envelope.task
        return {"task_id": task.task_id, "department_id": task.department_id, "status": task.status, "title": task.title}

    def _file_catalog(self, workspace_ref: str) -> list[dict[str, Any]]:
        if self.files is None:
            return []
        tree = self.files.load(workspace_ref)
        nodes = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        catalog: list[dict[str, Any]] = []
        for node in self.files._walk(nodes):
            if not isinstance(node, Mapping) or str(node.get("type") or "") == "folder":
                continue
            reference = str(node.get("id") or "").strip()
            label = str(node.get("name") or node.get("title") or "Untitled file").strip()
            if not reference:
                continue
            protection = self.files.protection(dict(node))
            catalog.append({
                "id": reference[:200], "label": label[:160],
                "document_type": str(node.get("document_type") or node.get("type") or "file")[:80],
                "status": str(node.get("status") or "available")[:80],
                "protected": bool(protection.get("protected")),
            })
            if len(catalog) >= 100:
                break
        return catalog

    @classmethod
    def _mobile_summary(cls, source: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"headline", "summary", "generated_at", "health", "queue", "approvals", "alerts", "pulse", "center", "departments", "work", "files"}
        projected = {key: source[key] for key in allowed if key in source}
        return cls._bounded_value(projected, depth=0)

    @classmethod
    def _bounded_value(cls, value: Any, *, depth: int) -> Any:
        if depth > 5:
            return "[summary depth limited]"
        if isinstance(value, Mapping):
            blocked = ("password", "secret", "token", "credential", "private_key", "api_key", "email", "phone")
            return {
                str(key)[:80]: cls._bounded_value(item, depth=depth + 1)
                for key, item in list(value.items())[:40]
                if not any(marker in str(key).casefold() for marker in blocked)
            }
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [cls._bounded_value(item, depth=depth + 1) for item in list(value)[:50]]
        if isinstance(value, str):
            return value[:500]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:200]


class WorkspaceProvider(Protocol):
    """Minimal provider boundary; provider data remains in its authoritative store."""

    provider_id: str

    def list_workspaces(self) -> Sequence[Mapping[str, Any]]: ...

    def describe_workspace(self, workspace_ref: str) -> Mapping[str, Any]: ...

    def read_surface(
        self, workspace_ref: str, surface: str, *, persona_id: str
    ) -> Mapping[str, Any]: ...

    def conversation_turn(
        self, workspace_ref: str, department_id: str, user_text: str, *, persona_id: str
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class WorkspaceBinding:
    provider_id: str
    provider_workspace_ref: str
    space: SpaceRef


class ProviderIndependentWorkspaceGateway:
    """Authority-first bridge between mobile Pilot and replaceable workspace providers.

    The gateway stores no Boardroom records. It binds a canonical SpaceRef to a provider
    reference, validates a separately issued membership, and requests only the named
    surface from the owning provider.
    """

    MAX_PROVIDERS = 16
    MAX_MEMBERSHIPS = 512
    MAX_SCOPES = 64
    ALLOWED_SURFACES = frozenset(
        {"overview", "briefings", "departments", "agents", "dashboards", "files", "packages", "decisions"}
    )

    MANIFEST_COLLECTIONS = (
        "departments", "agents", "dashboards", "files", "packages", "decisions"
    )

    def __init__(
        self,
        *,
        issuer_id: str = "",
        issuer_identity: DeviceIdentity | None = None,
        pairing_authority: MobilePairingAuthority | None = None,
        commercial_service: Any | None = None,
    ) -> None:
        self._providers: dict[str, WorkspaceProvider] = {}
        self._bindings: dict[str, WorkspaceBinding] = {}
        self._memberships: dict[str, Membership] = {}
        self._invitations: dict[str, dict[str, Any]] = {}
        self._invitation_replays: dict[str, str] = {}
        self._card_states: dict[str, dict[str, Any]] = {}
        self._card_replays: dict[str, dict[str, Any]] = {}
        self._signoff_packages: dict[str, dict[str, Any]] = {}
        self._signoff_replays: dict[str, dict[str, Any]] = {}
        self._cross_space_file_refs: dict[str, dict[str, Any]] = {}
        self._desktop_handoffs: dict[str, dict[str, Any]] = {}
        self._issuer_id = issuer_id
        self._issuer_identity = issuer_identity
        self._pairing = pairing_authority
        self._commercial = commercial_service

    def register_provider(self, provider: WorkspaceProvider) -> None:
        provider_id = str(getattr(provider, "provider_id", "")).strip()
        if not provider_id or len(provider_id) > 80:
            raise ValueError("provider_id is required and must be bounded")
        if provider_id not in self._providers and len(self._providers) >= self.MAX_PROVIDERS:
            raise ValueError("workspace provider limit reached")
        self._providers[provider_id] = provider

    def discover(self, provider_id: str) -> tuple[WorkspaceBinding, ...]:
        provider = self._provider(provider_id)
        records = provider.list_workspaces()
        if len(records) > 256:
            raise ValueError("provider returned too many workspaces")
        bindings: list[WorkspaceBinding] = []
        for record in records:
            provider_ref = str(record.get("id") or "").strip()
            if not provider_ref:
                continue
            space = adapt_workspace(record)
            binding = WorkspaceBinding(provider_id, provider_ref, space)
            self._bindings[space.space_id] = binding
            bindings.append(binding)
        return tuple(bindings)

    def grant_membership(self, membership: Membership) -> None:
        if membership.space_id not in self._bindings:
            raise ValueError("workspace is not bound to a registered provider")
        if len(membership.scopes) > self.MAX_SCOPES:
            raise ValueError("membership contains too many scopes")
        if membership.membership_id not in self._memberships and len(self._memberships) >= self.MAX_MEMBERSHIPS:
            raise ValueError("workspace membership limit reached")
        self._memberships[membership.membership_id] = membership

    def spaces_for(self, persona_id: str) -> tuple[dict[str, Any], ...]:
        visible: list[dict[str, Any]] = []
        for membership in self._memberships.values():
            if membership.persona_id != persona_id or not membership.is_active():
                continue
            binding = self._bindings.get(membership.space_id)
            if binding is None:
                continue
            visible.append(
                {
                    "space": binding.space.to_dict(),
                    "membership": membership.to_dict(),
                    "provider_id": binding.provider_id,
                }
            )
        return tuple(sorted(visible, key=lambda item: item["space"]["display_name"].casefold()))

    def surface_manifests_for(
        self, *, persona_id: str, device_id: str, surface_id: str, lease_id: str,
        ttl_seconds: int = 300,
    ) -> tuple[dict[str, Any], ...]:
        """Publish only active memberships and provider-declared read capabilities."""
        manifests: list[dict[str, Any]] = []
        for visible in self.spaces_for(persona_id):
            membership = dict(visible["membership"])
            binding = self._bindings.get(str(membership.get("space_id") or ""))
            if binding is None:
                continue
            descriptor = dict(self._provider(binding.provider_id).describe_workspace(binding.provider_workspace_ref))
            declared = {str(item) for item in descriptor.get("permitted_actions", ()) if str(item)}
            capabilities = [str(item) for item in membership.get("scopes", ()) if str(item) in declared]
            if not capabilities:
                continue
            manifests.append(self.publish_signed_manifest(
                persona_id=persona_id, membership_id=str(membership["membership_id"]),
                device_id=device_id, lease_id=lease_id, surface_id=surface_id,
                requested_capabilities=capabilities, ttl_seconds=ttl_seconds,
            ))
        return tuple(manifests[:24])

    def manage_membership(
        self,
        *,
        actor_persona_id: str,
        actor_membership_id: str,
        target_membership_id: str,
        operation: str,
        role_id: str = "",
        scopes: Sequence[str] = (),
        expires_at: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        actor = self._active_membership(actor_persona_id, actor_membership_id)
        if "workspace.members.manage" not in actor.scopes:
            raise PermissionError("membership does not permit member administration")
        target = self._memberships.get(target_membership_id)
        if target is None or target.space_id != actor.space_id:
            raise PermissionError("target membership is unavailable in this workspace")
        if operation not in {"change_role", "suspend", "restore", "revoke", "set_expiry"}:
            raise ValueError("unsupported membership operation")
        new_role = target.role_id
        new_scopes = target.scopes
        new_status = target.status
        new_expiry = target.expires_at
        if operation == "change_role":
            offered = tuple(dict.fromkeys(str(item) for item in scopes if str(item)))
            if not role_id or not offered:
                raise ValueError("role and exact scopes are required")
            grantable = set(actor.scopes).difference({"workspace.members.manage"})
            if set(offered).difference(grantable):
                raise PermissionError("administrator cannot grant scopes they do not hold")
            new_role, new_scopes = role_id, offered
        elif operation == "suspend":
            new_status = "suspended"
        elif operation == "restore":
            if target.status != "suspended":
                raise ValueError("only a suspended membership can be restored")
            new_status = "active"
        elif operation == "revoke":
            new_status = "revoked"
        elif operation == "set_expiry":
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if parsed <= datetime.now(timezone.utc):
                raise ValueError("membership expiry must be in the future")
            new_expiry = parsed.isoformat()
        changed = Membership(
            membership_id=target.membership_id,
            persona_id=target.persona_id,
            space_id=target.space_id,
            role_id=new_role,
            scopes=new_scopes,
            status=new_status,
            issued_at=target.issued_at,
            expires_at=new_expiry,
            revision=target.revision + 1,
        )
        self._memberships[target_membership_id] = changed
        return {
            "membership": changed.to_dict(),
            "receipt": {
                "operation": operation,
                "actor_persona_id": actor_persona_id,
                "reason": " ".join(reason.split())[:240],
                "recorded_at": utc_now_iso(),
                "membership_hash": changed.contract_hash(),
                "immediately_enforced": True,
            },
        }

    def read(
        self,
        *,
        persona_id: str,
        membership_id: str,
        surface: str,
    ) -> dict[str, Any]:
        if surface not in self.ALLOWED_SURFACES:
            raise ValueError("workspace surface is not supported")
        membership = self._active_membership(persona_id, membership_id)
        required_scope = f"workspace.{surface}.read"
        if required_scope not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError(f"membership does not permit {required_scope}")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        result = dict(
            provider.read_surface(binding.provider_workspace_ref, surface, persona_id=persona_id)
        )
        self._validate_provider_result(result)
        self._assert_no_personal_payload(result.get("data", {}))
        return {
            "ok": True,
            "space": binding.space.to_dict(),
            "membership_id": membership.membership_id,
            "surface": surface,
            "provider_id": binding.provider_id,
            "provider_revision": result.get("revision"),
            "data": result.get("data", {}),
            "retrieved_at": utc_now_iso(),
            "projection_hash": canonical_hash(result.get("data", {})),
            "authority": "active_membership",
            "source_of_truth": "workspace_provider",
        }

    def conversation_turn(
        self,
        *,
        persona_id: str,
        membership_id: str,
        department_id: str,
        user_text: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        department = " ".join(str(department_id or "boardroom").split()).casefold()[:80]
        required_scope = f"workspace.department.{department}.conversation"
        if "workspace.conversation" not in membership.scopes and required_scope not in membership.scopes:
            raise PermissionError("membership does not permit this workspace conversation")
        question = " ".join(str(user_text or "").split())[:2_000]
        if not question:
            raise ValueError("workspace conversation text is required")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "conversation_turn", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support governed conversation")
        result = dict(handler(
            binding.provider_workspace_ref, department, question, persona_id=persona_id
        ))
        if bool(result.get("external_writes_performed")):
            raise ValueError("workspace conversation provider attempted an external write")
        turn = result.get("turn")
        if not isinstance(turn, Mapping) or not str(turn.get("content") or "").strip():
            raise ValueError("workspace conversation provider returned an invalid turn")
        if len(str(result).encode("utf-8")) > 256_000:
            raise ValueError("workspace conversation response exceeds the mobile limit")
        return {
            "ok": True,
            "space": binding.space.to_dict(),
            "membership_id": membership.membership_id,
            "department_id": department,
            "provider_id": binding.provider_id,
            "conversation": result,
            "question_hash": canonical_hash({"question": question}),
            "retrieved_at": utc_now_iso(),
            "authority": "active_membership",
            "source_of_truth": "workspace_provider",
            "external_writes_performed": False,
        }

    def review_cards(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.cards.read" not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError("membership does not permit workspace review cards")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        result = dict(provider.read_surface(binding.provider_workspace_ref, "departments", persona_id=persona_id))
        self._validate_provider_result(result)
        work = result.get("data", {}).get("work", []) if isinstance(result.get("data"), Mapping) else []
        cards: list[dict[str, Any]] = []
        for item in work[:100] if isinstance(work, list) else []:
            if not isinstance(item, Mapping):
                continue
            source_ref = str(item.get("task_id") or "").strip()
            if not source_ref:
                continue
            key = f"{membership.space_id}:{source_ref}"
            base = {
                "card_id": f"card/{canonical_hash({'space_id': membership.space_id, 'source_ref': source_ref})[:24]}",
                "space_id": membership.space_id,
                "source_ref": source_ref,
                "department_id": str(item.get("department_id") or "")[:80],
                "title": str(item.get("title") or "Untitled work")[:200],
                "source_status": str(item.get("status") or "unknown")[:80],
                "state": "ready_for_review",
                "revision": 1,
            }
            current = self._card_states.get(key)
            if current:
                base.update(current)
            base["scope_hash"] = canonical_hash({k: v for k, v in base.items() if k != "scope_hash"})
            cards.append(base)
        return {
            "ok": True, "space": binding.space.to_dict(), "membership_id": membership_id,
            "cards": cards, "provider_revision": result.get("revision"), "private_phone_only": True,
            "external_writes_performed": False,
        }

    def act_on_review_card(
        self,
        *,
        persona_id: str,
        membership_id: str,
        card_id: str,
        operation: str,
        expected_scope_hash: str,
        correction: str = "",
        recipient_ref: str = "",
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        required = "workspace.approve" if operation == "approve" else "workspace.cards.act"
        if required not in membership.scopes:
            raise PermissionError(f"membership does not permit {required}")
        if operation not in {"review", "correct", "delegate", "approve"}:
            raise ValueError("unsupported workspace review-card operation")
        clean_correction = " ".join(correction.split())[:2_000]
        clean_recipient = " ".join(recipient_ref.split())[:200]
        if operation == "correct" and not clean_correction:
            raise ValueError("correction text is required")
        if operation == "delegate" and not clean_recipient:
            raise ValueError("an exact delegation recipient is required")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "card_id": card_id,
            "operation": operation, "scope_hash": expected_scope_hash,
            "correction": clean_correction, "recipient_ref": clean_recipient,
        })
        replay = self._card_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different card action")
            return dict(replay["result"])
        snapshot = self.review_cards(persona_id=persona_id, membership_id=membership_id)
        card = next((dict(item) for item in snapshot["cards"] if item["card_id"] == card_id), None)
        if card is None:
            raise LookupError("workspace review card was not found")
        if card["scope_hash"] != expected_scope_hash:
            raise PermissionError("workspace review card changed before action")
        state = {
            "review": "reviewed", "correct": "correction_requested",
            "delegate": "delegation_prepared", "approve": "approved",
        }[operation]
        stored = {
            "state": state, "revision": int(card["revision"]) + 1,
            "last_operation": operation, "acted_by": persona_id, "acted_at": utc_now_iso(),
        }
        if clean_correction:
            stored["correction"] = clean_correction
        if clean_recipient:
            stored["recipient_ref"] = clean_recipient
        key = f"{membership.space_id}:{card['source_ref']}"
        self._card_states[key] = stored
        receipt = {
            "operation": operation, "card_id": card_id, "previous_scope_hash": expected_scope_hash,
            "actor_persona_id": persona_id, "membership_id": membership_id,
            "recorded_at": stored["acted_at"], "external_write_performed": False,
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        result = {"ok": True, "state": state, "receipt": receipt, "approval_is_execution": False}
        self._card_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def prepare_signoff_package(
        self,
        *,
        persona_id: str,
        membership_id: str,
        card_id: str,
        expected_scope_hash: str,
        signatory_role: str,
        statement: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.signoff.prepare" not in membership.scopes:
            raise PermissionError("membership does not permit sign-off package preparation")
        role = str(signatory_role or "").casefold().strip()
        if role not in {"accountant", "auditor", "adviser", "director"}:
            raise ValueError("unsupported professional signatory role")
        declaration = " ".join(str(statement or "").split())[:2_000]
        if not declaration:
            raise ValueError("sign-off statement is required")
        snapshot = self.review_cards(persona_id=persona_id, membership_id=membership_id)
        card = next((dict(item) for item in snapshot["cards"] if item["card_id"] == card_id), None)
        if card is None:
            raise LookupError("workspace review card was not found")
        if card["scope_hash"] != expected_scope_hash:
            raise PermissionError("workspace review card changed before sign-off preparation")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "card_id": card_id,
            "scope_hash": expected_scope_hash, "role": role, "statement": declaration,
        })
        replay = self._signoff_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different sign-off package")
            return dict(replay["result"])
        package_id = f"signoff/{canonical_hash({'request_hash': request_hash, 'idempotency_key': idempotency_key})[:24]}"
        package = {
            "schema_version": "pilot.workspace-signoff-package.v1",
            "package_id": package_id,
            "space_id": membership.space_id,
            "source_card_id": card_id,
            "source_scope_hash": expected_scope_hash,
            "source_ref": card["source_ref"],
            "title": card["title"],
            "signatory_role": role,
            "statement": declaration,
            "prepared_by": persona_id,
            "prepared_at": utc_now_iso(),
            "status": "awaiting_signoff",
            "revision": 1,
        }
        package["package_hash"] = canonical_hash(package)
        self._signoff_packages[package_id] = package
        result = {"ok": True, "package": dict(package), "external_write_performed": False}
        self._signoff_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def signoff_packages(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.signoff.read" not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError("membership does not permit sign-off package review")
        packages = [dict(item) for item in self._signoff_packages.values() if item["space_id"] == membership.space_id]
        return {
            "ok": True, "space_id": membership.space_id, "membership_id": membership_id,
            "packages": sorted(packages, key=lambda item: item["prepared_at"], reverse=True)[:100],
            "private_phone_only": True,
        }

    def decide_signoff_package(
        self,
        *,
        persona_id: str,
        membership_id: str,
        package_id: str,
        expected_package_hash: str,
        decision: str,
        professional_reference: str,
        phone_device_id: str,
        phone_signature: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        package = self._signoff_packages.get(package_id)
        if package is None or package["space_id"] != membership.space_id:
            raise LookupError("sign-off package was not found in this workspace")
        exact_scope = f"workspace.signoff.{package['signatory_role']}"
        if "workspace.signoff" not in membership.scopes and exact_scope not in membership.scopes:
            raise PermissionError("membership does not permit this professional sign-off role")
        if decision not in {"signed", "rejected"}:
            raise ValueError("sign-off decision must be signed or rejected")
        reference = " ".join(str(professional_reference or "").split())[:240]
        if decision == "signed" and not reference:
            raise ValueError("professional reference or capacity declaration is required")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "package_id": package_id,
            "expected_package_hash": expected_package_hash, "decision": decision,
            "professional_reference": reference,
        })
        replay = self._signoff_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different sign-off decision")
            return dict(replay["result"])
        if package["status"] != "awaiting_signoff" or package["package_hash"] != expected_package_hash:
            raise PermissionError("sign-off package changed or is no longer awaiting sign-off")
        receipt = {
            "schema_version": "pilot.workspace-signoff-receipt.v1",
            "package_id": package_id, "package_hash": expected_package_hash,
            "decision": decision, "signatory_role": package["signatory_role"],
            "signer_persona_id": persona_id, "signer_membership_id": membership_id,
            "phone_device_id": phone_device_id, "phone_signature_hash": canonical_hash({"signature": phone_signature}),
            "professional_reference": reference, "signed_at": utc_now_iso(),
            "external_write_performed": False,
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        package.update({"status": decision, "revision": int(package["revision"]) + 1, "signoff_receipt": receipt})
        result = {"ok": True, "package": dict(package), "receipt": receipt, "independently_verifiable": True}
        self._signoff_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def create_cross_space_file_reference(
        self,
        *,
        persona_id: str,
        source_membership_id: str,
        target_membership_id: str,
        file_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        source = self._active_membership(persona_id, source_membership_id)
        target = self._active_membership(persona_id, target_membership_id)
        if source.space_id == target.space_id:
            raise ValueError("cross-space reference requires two different workspaces")
        if "workspace.files.read" not in source.scopes and "workspace.read" not in source.scopes:
            raise PermissionError("source membership does not permit file references")
        if "workspace.files.reference" not in target.scopes:
            raise PermissionError("target membership does not permit cross-space file references")
        source_binding = self._bindings[source.space_id]
        provider = self._provider(source_binding.provider_id)
        result = dict(provider.read_surface(source_binding.provider_workspace_ref, "files", persona_id=persona_id))
        self._validate_provider_result(result)
        files = result.get("data", {}).get("files", []) if isinstance(result.get("data"), Mapping) else []
        item = next((dict(row) for row in files if isinstance(row, Mapping) and str(row.get("id") or "") == file_id), None)
        if item is None:
            raise LookupError("organization file was not found")
        request_hash = canonical_hash({
            "persona_id": persona_id, "source_membership_id": source_membership_id,
            "target_membership_id": target_membership_id, "file_id": file_id,
        })
        existing = self._cross_space_file_refs.get(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for another file reference")
            return dict(existing["result"])
        reference = {
            "schema_version": "pilot.workspace-file-reference.v1",
            "reference_id": f"workspace-file-ref/{canonical_hash({'request_hash': request_hash, 'key': idempotency_key})[:24]}",
            "source_space_id": source.space_id,
            "target_space_id": target.space_id,
            "organization_file_id": file_id,
            "label": str(item.get("label") or "Organization file")[:160],
            "document_type": str(item.get("document_type") or "file")[:80],
            "protected": bool(item.get("protected")),
            "access_mode": "reference_only_reauthorize_at_source",
            "content_included": False,
            "storage_path_included": False,
            "created_by": persona_id,
            "created_at": utc_now_iso(),
        }
        reference["reference_hash"] = canonical_hash(reference)
        result_value = {"ok": True, "reference": reference, "bytes_copied": 0, "source_ownership_preserved": True}
        self._cross_space_file_refs[idempotency_key] = {"request_hash": request_hash, "result": result_value}
        return result_value

    def cross_space_file_references(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.files.reference" not in membership.scopes:
            raise PermissionError("membership does not permit cross-space file references")
        references = [
            dict(record["result"]["reference"]) for record in self._cross_space_file_refs.values()
            if record["result"]["reference"]["target_space_id"] == membership.space_id
        ]
        return {"ok": True, "space_id": membership.space_id, "references": references, "content_included": False}

    def prepare_desktop_handoff(
        self,
        *,
        persona_id: str,
        membership_id: str,
        purpose: str,
        idempotency_key: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.desktop.handoff" not in membership.scopes:
            raise PermissionError("membership does not permit desktop handoff")
        if self._issuer_identity is None or not self._issuer_id:
            raise RuntimeError("desktop handoff signing identity is unavailable")
        intent = " ".join(str(purpose or "").split())[:240]
        if not intent:
            raise ValueError("desktop handoff purpose is required")
        if ttl_seconds < 60 or ttl_seconds > 900:
            raise ValueError("desktop handoff lifetime must be between one and fifteen minutes")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "purpose": intent,
            "ttl_seconds": ttl_seconds,
        })
        existing = self._desktop_handoffs.get(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for another desktop handoff")
            return dict(existing["result"])
        now = datetime.now(timezone.utc).replace(microsecond=0)
        binding = self._bindings[membership.space_id]
        token = canonical_hash({"request_hash": request_hash, "nonce": uuid4().hex, "issued_at": now.isoformat()})
        ticket = {
            "schema_version": "pilot.desktop-handoff.v1",
            "handoff_id": f"handoff/{token[:24]}", "token": token,
            "token_hash": canonical_hash({"token": token}),
            "issuer_id": self._issuer_id, "issuer_public_key": self._issuer_identity.public_key_b64,
            "persona_id": persona_id, "membership_id": membership_id,
            "space_id": membership.space_id, "provider_id": binding.provider_id,
            "provider_workspace_ref": binding.provider_workspace_ref,
            "purpose": intent, "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            "authentication_required": True, "grants_workspace_access": False,
        }
        signed_payload = {key: value for key, value in ticket.items() if key != "token"}
        ticket["ticket_hash"] = canonical_hash(signed_payload)
        ticket["signature"] = self._issuer_identity.sign(canonical_bytes(signed_payload))
        result = {
            "ok": True, "ticket": ticket,
            "desktop_path": f"/aion-business?workspace_id={binding.provider_workspace_ref}&pilot_handoff={token}",
            "instruction": "Continue on desktop and authenticate there. This handoff does not grant access.",
        }
        self._desktop_handoffs[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def publish_signed_manifest(
        self,
        *,
        persona_id: str,
        membership_id: str,
        device_id: str,
        lease_id: str,
        surface_id: str,
        requested_capabilities: Sequence[str],
        redactions: Sequence[str] = (),
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        if self._issuer_identity is None or not self._issuer_id:
            raise RuntimeError("workspace manifest signing identity is unavailable")
        if ttl_seconds < 30 or ttl_seconds > 900:
            raise ValueError("workspace manifest lifetime must be between 30 and 900 seconds")
        membership = self._active_membership(persona_id, membership_id)
        capabilities = tuple(dict.fromkeys(str(item) for item in requested_capabilities if str(item)))
        if not capabilities or len(capabilities) > self.MAX_SCOPES:
            raise ValueError("workspace manifest capabilities are empty or excessive")
        unauthorized = set(capabilities).difference(membership.scopes)
        if unauthorized:
            raise PermissionError("workspace manifest requested capabilities outside the membership")
        binding = self._bindings[membership.space_id]
        descriptor = dict(
            self._provider(binding.provider_id).describe_workspace(binding.provider_workspace_ref)
        )
        catalog = self._bounded_catalog(descriptor)
        declared_actions = {
            str(item) for item in descriptor.get("permitted_actions", ()) if str(item)
        }
        permitted_actions = tuple(item for item in capabilities if item in declared_actions)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires = now + timedelta(seconds=ttl_seconds)
        seed = {
            "surface_id": surface_id,
            "persona_id": persona_id,
            "space_id": membership.space_id,
            "lease_id": lease_id,
            "issued_at": now.isoformat(),
        }
        manifest = SurfaceManifest(
            manifest_id=f"manifest/{canonical_hash(seed)[:24]}",
            surface_id=surface_id,
            persona_id=persona_id,
            space_id=membership.space_id,
            lease_id=lease_id,
            capabilities=permitted_actions,
            redactions=tuple(dict.fromkeys(str(item) for item in redactions if str(item)))[:32],
            issued_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )
        payload = {
            "schema_version": "pilot.workspace-manifest.v1",
            "issuer_id": self._issuer_id,
            "issuer_public_key": self._issuer_identity.public_key_b64,
            "provider_id": binding.provider_id,
            "membership_id": membership.membership_id,
            "space": binding.space.to_dict(),
            "membership_summary": {
                "membership_id": membership.membership_id, "role_id": membership.role_id,
                "revision": membership.revision,
            },
            "manifest": manifest.to_dict(),
            "catalog": catalog,
        }
        return {
            **payload,
            "payload_hash": canonical_hash(payload),
            "signature": self._issuer_identity.sign(canonical_bytes(payload)),
        }

    def create_invitation(
        self,
        *,
        inviter_persona_id: str,
        inviter_membership_id: str,
        recipient_ref: str,
        role_id: str,
        requested_scopes: Sequence[str],
        constraints: Mapping[str, Any] | None = None,
        expires_in_seconds: int = 86_400,
        idempotency_key: str,
    ) -> dict[str, Any]:
        inviter = self._active_membership(inviter_persona_id, inviter_membership_id)
        if "workspace.invite" not in inviter.scopes:
            raise PermissionError("membership does not permit workspace invitations")
        scopes = tuple(dict.fromkeys(str(item) for item in requested_scopes if str(item)))
        if not scopes or len(scopes) > self.MAX_SCOPES:
            raise ValueError("invitation scopes are empty or excessive")
        grantable = set(inviter.scopes).difference({"workspace.invite"})
        if set(scopes).difference(grantable):
            raise PermissionError("invitation cannot grant scopes the inviter does not hold")
        if expires_in_seconds < 300 or expires_in_seconds > 2_592_000:
            raise ValueError("invitation lifetime must be between five minutes and 30 days")
        safe_constraints = self._bounded_constraints(constraints or {})
        fingerprint = canonical_hash(
            {
                "inviter_persona_id": inviter_persona_id,
                "membership_id": inviter_membership_id,
                "recipient_ref": recipient_ref,
                "role_id": role_id,
                "scopes": scopes,
                "constraints": safe_constraints,
                "expires_in_seconds": expires_in_seconds,
            }
        )
        replay = self._invitation_replays.get(idempotency_key)
        if replay:
            existing = self._invitations[replay]
            if existing["request_hash"] != fingerprint:
                raise ValueError("idempotency key was already used for different invitation scope")
            return dict(existing)
        if len(self._invitations) >= 1_024:
            raise ValueError("workspace invitation limit reached")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        seed = {"idempotency_key": idempotency_key, "request_hash": fingerprint, "created_at": now.isoformat()}
        invitation_id = f"invite/{canonical_hash(seed)[:24]}"
        invitation = Invitation(
            invitation_id=invitation_id,
            space_id=inviter.space_id,
            inviter_persona_id=inviter_persona_id,
            recipient_ref=recipient_ref,
            role_id=role_id,
            requested_scopes=scopes,
            state=InvitationState.PENDING,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=expires_in_seconds)).isoformat(),
        )
        record = {
            "invitation": invitation.to_dict(),
            "organization": self._bindings[inviter.space_id].space.to_dict(),
            "constraints": safe_constraints,
            "revocation_route": f"/v1/workspaces/invitations/{invitation_id.split('/', 1)[1]}/revoke",
            "request_hash": fingerprint,
        }
        self._invitations[invitation_id] = record
        self._invitation_replays[idempotency_key] = invitation_id
        return dict(record)

    def revoke_invitation(
        self, *, invitation_id: str, actor_persona_id: str, actor_membership_id: str
    ) -> dict[str, Any]:
        actor = self._active_membership(actor_persona_id, actor_membership_id)
        record = self._invitations.get(invitation_id)
        if record is None:
            raise LookupError("workspace invitation was not found")
        invitation_data = dict(record["invitation"])
        invitation_data.pop("schema_version", None)
        invitation_data["state"] = InvitationState(invitation_data["state"])
        invitation_data["requested_scopes"] = tuple(invitation_data["requested_scopes"])
        current = Invitation(**invitation_data)
        if actor.space_id != current.space_id:
            raise PermissionError("invitation belongs to a different workspace")
        if actor_persona_id != current.inviter_persona_id and "workspace.invite.revoke" not in actor.scopes:
            raise PermissionError("membership cannot revoke this invitation")
        if current.state == InvitationState.REVOKED:
            return dict(record)
        if current.state != InvitationState.PENDING:
            raise ValueError("only a pending invitation can be revoked")
        revoked = Invitation(
            invitation_id=current.invitation_id,
            space_id=current.space_id,
            inviter_persona_id=current.inviter_persona_id,
            recipient_ref=current.recipient_ref,
            role_id=current.role_id,
            requested_scopes=current.requested_scopes,
            state=InvitationState.REVOKED,
            created_at=current.created_at,
            expires_at=current.expires_at,
            revoked_at=utc_now_iso(),
        )
        record["invitation"] = revoked.to_dict()
        return dict(record)

    def invitation_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.invitations.read",
        )
        invitations = []
        for record in self._invitations.values():
            invitation = record["invitation"]
            if invitation["recipient_ref"] not in {persona_id, f"person/{persona_id}"}:
                continue
            invitations.append(self._invitation_view(record))
        return {"ok": True, "persona_id": persona_id, "invitations": invitations, "private_phone_only": True}

    def mobile_read_surface(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        return self.read(
            persona_id=persona_id,
            membership_id=str(request.get("membership_id") or ""),
            surface=str(request.get("surface") or "overview"),
        )

    def mobile_conversation_turn(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.conversation_turn(
            persona_id=persona_id,
            membership_id=str(request.get("membership_id") or ""),
            department_id=str(request.get("department_id") or "boardroom"),
            user_text=str(request.get("user_text") or ""),
        )

    def mobile_review_cards(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.cards.read",
        )
        return self.review_cards(persona_id=persona_id, membership_id=str(request.get("membership_id") or ""))

    def mobile_review_card_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        operation = str(request.get("operation") or "")
        phone_scope = "workspace.approve" if operation == "approve" else "workspace.cards.act"
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope=phone_scope,
        )
        return self.act_on_review_card(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            card_id=str(request.get("card_id") or ""), operation=operation,
            expected_scope_hash=str(request.get("expected_scope_hash") or ""),
            correction=str(request.get("correction") or ""), recipient_ref=str(request.get("recipient_ref") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_prepare_signoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff.prepare",
        )
        return self.prepare_signoff_package(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            card_id=str(request.get("card_id") or ""), expected_scope_hash=str(request.get("expected_scope_hash") or ""),
            signatory_role=str(request.get("signatory_role") or ""), statement=str(request.get("statement") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_signoff_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff.read",
        )
        return self.signoff_packages(persona_id=persona_id, membership_id=str(request.get("membership_id") or ""))

    def mobile_decide_signoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff",
        )
        return self.decide_signoff_package(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            package_id=str(request.get("package_id") or ""), expected_package_hash=str(request.get("expected_package_hash") or ""),
            decision=str(request.get("decision") or ""), professional_reference=str(request.get("professional_reference") or ""),
            phone_device_id=str(certificate.get("device_id") or ""), phone_signature=phone_signature,
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_create_file_reference(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.files.reference",
        )
        return self.create_cross_space_file_reference(
            persona_id=persona_id, source_membership_id=str(request.get("source_membership_id") or ""),
            target_membership_id=str(request.get("target_membership_id") or ""), file_id=str(request.get("file_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_file_references(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.files.reference",
        )
        return self.cross_space_file_references(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or "")
        )

    def mobile_prepare_desktop_handoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.desktop.handoff",
        )
        return self.prepare_desktop_handoff(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            purpose=str(request.get("purpose") or "Continue workspace work"),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_commercial_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.commercial.read",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.commercial.read" not in membership.scopes:
            raise PermissionError("membership does not permit commercial status")
        if self._commercial is None:
            raise RuntimeError("commercial adoption service is unavailable")
        binding = self._bindings[membership.space_id]
        dashboard = dict(self._commercial.customer_dashboard(tenant_id=binding.provider_workspace_ref))
        if dashboard.get("private_content_included") is not False:
            raise ValueError("commercial dashboard crossed the private-content boundary")
        return {
            "ok": True, "membership_id": membership.membership_id,
            "space": binding.space.to_dict(), "dashboard": dashboard,
            "private_phone_only": True, "external_writes_performed": False,
        }

    def mobile_commercial_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.commercial.control",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.commercial.control" not in membership.scopes:
            raise PermissionError("membership does not permit commercial control")
        if self._commercial is None:
            raise RuntimeError("commercial adoption service is unavailable")
        binding = self._bindings[membership.space_id]
        tenant_id = binding.provider_workspace_ref
        operation = str(request.get("operation") or "")
        if operation == "start_trial":
            now = datetime.now(timezone.utc)
            days = int(request.get("days") or 30)
            if not 1 <= days <= 90:
                raise ValueError("trial period must be between 1 and 90 days")
            result = self._commercial.start_trial(
                trial_id=f"trial.{uuid4().hex}", tenant_id=tenant_id,
                department=str(request.get("department") or ""), actor_id=persona_id,
                starts_at=now.isoformat(), ends_at=(now + timedelta(days=days)).isoformat(),
                action_limit=int(request.get("action_limit") or 0),
                managed_cost_limit=float(request.get("managed_cost_limit") or 0),
                currency=str(request.get("currency") or "EUR"),
                offer_version=str(request.get("offer_version") or ""),
                consent_ref=str(request.get("consent_ref") or ""), auto_renew=False,
            )
        elif operation == "cancel_trial":
            trial_id = str(request.get("trial_id") or "")
            current = self._commercial.trial_status(trial_id=trial_id)
            if current.get("tenant_id") != tenant_id:
                raise PermissionError("trial belongs to another workspace")
            result = self._commercial.cancel(
                trial_id=trial_id, actor_id=persona_id,
                cancellation_ref=str(request.get("cancellation_ref") or ""),
            )
        elif operation == "set_capacity":
            result = self._commercial.set_capacity_control(
                tenant_id=tenant_id, department=str(request.get("department") or ""),
                actor_id=persona_id, monthly_action_limit=int(request.get("monthly_action_limit") or 0),
                overage_allowed=bool(request.get("overage_allowed")),
                overage_approval_ref=str(request.get("overage_approval_ref") or ""),
            )
        else:
            raise ValueError("unsupported commercial operation")
        return {
            "ok": True, "operation": operation, "result": result,
            "dashboard": self._commercial.customer_dashboard(tenant_id=tenant_id),
            "membership_id": membership.membership_id, "private_phone_only": True,
        }

    def respond_to_invitation(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.invitations.respond",
        )
        invitation_id = str(request.get("invitation_id") or "")
        decision = str(request.get("decision") or "")
        if decision not in {"accepted", "declined"}:
            raise ValueError("invitation decision must be accepted or declined")
        record = self._invitations.get(invitation_id)
        if record is None:
            raise LookupError("workspace invitation was not found")
        data = dict(record["invitation"])
        if data["recipient_ref"] not in {persona_id, f"person/{persona_id}"}:
            raise PermissionError("workspace invitation belongs to another person")
        if data["state"] != "pending":
            if data["state"] == decision:
                return self._invitation_view(record)
            raise ValueError("workspace invitation is no longer pending")
        expires = datetime.fromisoformat(str(data["expires_at"]).replace("Z", "+00:00"))
        if expires <= datetime.now(timezone.utc):
            data["state"] = "expired"
            record["invitation"] = data
            raise PermissionError("workspace invitation has expired")
        data["state"] = decision
        if decision == "accepted":
            data["accepted_by_persona_id"] = persona_id
            membership = Membership(
                membership_id=f"membership/{canonical_hash({'invitation_id': invitation_id, 'persona_id': persona_id})[:24]}",
                persona_id=persona_id,
                space_id=str(data["space_id"]),
                role_id=str(data["role_id"]),
                scopes=tuple(data["requested_scopes"]),
                status="active",
                issued_at=utc_now_iso(),
                expires_at=str(data["expires_at"]),
            )
            self.grant_membership(membership)
            record["membership"] = membership.to_dict()
        record["invitation"] = data
        record["decision_receipt"] = {
            "decision": decision,
            "persona_id": persona_id,
            "device_id": certificate.get("device_id"),
            "scope_hash": canonical_hash({"invitation_id": invitation_id, "decision": decision}),
            "recorded_at": utc_now_iso(),
        }
        return self._invitation_view(record)

    @staticmethod
    def verify_signed_manifest(
        envelope: Mapping[str, Any], *, expected_persona_id: str = "", expected_device_id: str = ""
    ) -> bool:
        try:
            required = (
                "schema_version", "issuer_id", "issuer_public_key", "provider_id",
                "membership_id", "manifest", "catalog",
            )
            payload = {key: envelope[key] for key in required}
            for optional in ("space", "membership_summary"):
                if optional in envelope:
                    payload[optional] = envelope[optional]
            if payload["schema_version"] != "pilot.workspace-manifest.v1":
                return False
            if canonical_hash(payload) != envelope.get("payload_hash"):
                return False
            if not DeviceIdentity.verify(
                str(payload["issuer_public_key"]), canonical_bytes(payload), str(envelope.get("signature") or "")
            ):
                return False
            manifest = payload["manifest"]
            if expected_persona_id and manifest.get("persona_id") != expected_persona_id:
                return False
            if expected_device_id and manifest.get("surface_id") != expected_device_id:
                return False
            expiry = datetime.fromisoformat(str(manifest["expires_at"]).replace("Z", "+00:00"))
            return expiry > datetime.now(timezone.utc)
        except (KeyError, TypeError, ValueError):
            return False

    def _active_membership(self, persona_id: str, membership_id: str) -> Membership:
        membership = self._memberships.get(membership_id)
        if membership is None or membership.persona_id != persona_id:
            raise PermissionError("workspace membership is unavailable")
        if not membership.is_active(now=datetime.now(timezone.utc)):
            raise PermissionError("workspace membership is inactive or expired")
        if membership.space_id not in self._bindings:
            raise PermissionError("workspace provider binding is unavailable")
        return membership

    def _provider(self, provider_id: str) -> WorkspaceProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise LookupError("workspace provider is not registered")
        return provider

    def _authorize_phone(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, scope: str,
    ) -> str:
        if self._pairing is None:
            raise RuntimeError("workspace phone authority is unavailable")
        authority = self._pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        return str(authority["persona_id"])

    @staticmethod
    def _invitation_view(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in record.items()
            if key in {"invitation", "organization", "constraints", "revocation_route", "membership", "decision_receipt"}
        }

    @staticmethod
    def _bounded_constraints(constraints: Mapping[str, Any]) -> dict[str, Any]:
        if len(constraints) > 16:
            raise ValueError("invitation has too many constraints")
        allowed = {"departments", "regions", "project_refs", "approval_limit", "working_hours", "notes"}
        if set(constraints).difference(allowed):
            raise ValueError("invitation contains an unsupported constraint")
        if len(str(constraints).encode("utf-8")) > 8_192:
            raise ValueError("invitation constraints exceed the size limit")
        return dict(constraints)

    @staticmethod
    def _validate_provider_result(result: Mapping[str, Any]) -> None:
        if not isinstance(result.get("data", {}), Mapping):
            raise ValueError("workspace provider data must be a mapping")
        encoded_size = len(str(result).encode("utf-8"))
        if encoded_size > 1_000_000:
            raise ValueError("workspace provider response exceeds the mobile projection limit")

    @classmethod
    def _assert_no_personal_payload(cls, value: Any, *, depth: int = 0) -> None:
        if depth > 8:
            return
        prohibited = {
            "personal_pilot", "personal_memory", "private_identity", "private_calendar",
            "personal_calendar", "personal_tasks", "guardian_controlled_children",
            "home_devices", "household_location", "payment_methods",
        }
        if isinstance(value, Mapping):
            for key, item in value.items():
                normalized = str(key).casefold().replace("-", "_").replace(" ", "_")
                if normalized in prohibited:
                    raise PermissionError("workspace provider attempted to expose Personal Pilot data")
                cls._assert_no_personal_payload(item, depth=depth + 1)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in list(value)[:1_000]:
                cls._assert_no_personal_payload(item, depth=depth + 1)

    @classmethod
    def _bounded_catalog(cls, descriptor: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
        catalog: dict[str, list[dict[str, str]]] = {}
        for collection in cls.MANIFEST_COLLECTIONS:
            items = descriptor.get(collection, ())
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or len(items) > 100:
                raise ValueError(f"workspace {collection} manifest is invalid or excessive")
            normalized: list[dict[str, str]] = []
            for item in items:
                if not isinstance(item, Mapping):
                    raise ValueError(f"workspace {collection} item must be a mapping")
                reference = str(item.get("id") or "").strip()
                label = str(item.get("label") or item.get("name") or "").strip()
                if not reference or len(reference) > 200 or not label or len(label) > 160:
                    raise ValueError(f"workspace {collection} item is not bounded")
                normalized.append({"id": reference, "label": label})
            catalog[collection] = normalized
        return catalog
