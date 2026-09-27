"""AION Pilot Model Harness: a controlled bridge from a Pilot to a model.

Boundary:
- AION owns business memory, routing, permissions, approval and execution.
- The Pilot owns the business workflow and task authority.
- This harness renders one Pilot-owned request for a model, parses the answer,
  validates it, and emits a receipt.  It never executes a tool or mutates state.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping


HARNESS_SCHEMA = "aion.pilot_model_harness.v1"
GPT_OSS_HARMONY_ADAPTER = "gpt_oss_harmony.v1"


class PilotModelHarnessError(ValueError):
    """Raised when a Pilot request or model proposal crosses the harness boundary."""


# The first GPT-OSS private-reasoning pack deliberately offers only observable,
# non-executing capabilities.  AION's existing gateway owns actual invocation.
GPT_OSS_PRIVATE_REASONING_TOOLS: dict[str, dict[str, Any]] = {
    "retrieve_business_facts": {
        "mode": "read",
        "description": "Retrieve source-referenced facts already authorised for this Pilot.",
        "arguments_schema": {"type": "object", "required": ["query"]},
    },
    "calculate_finance": {
        "mode": "deterministic",
        "description": "Calculate totals, VAT, variances or other declared arithmetic.",
        "arguments_schema": {"type": "object", "required": ["calculation"]},
    },
    "classify_business_item": {
        "mode": "read",
        "description": "Classify a supplied business item against the Pilot taxonomy.",
        "arguments_schema": {"type": "object", "required": ["item", "taxonomy"]},
    },
    "prepare_business_draft": {
        "mode": "draft",
        "description": "Prepare a reviewable draft. It cannot send, publish or write records.",
        "arguments_schema": {"type": "object", "required": ["purpose"]},
    },
    "request_exact_approval": {
        "mode": "approval_request",
        "description": "Request human review for one exact proposed external payload.",
        "arguments_schema": {"type": "object", "required": ["reason", "proposed_payload"]},
    },
}

_FORBIDDEN_KEYS = {
    "chain_of_thought", "hidden_reasoning", "private_reasoning", "raw_tool_call",
    "execute_now", "send_now", "publish_now", "write_now", "api_key", "secret",
    "password", "access_token", "refresh_token", "credential", "credentials",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _redact(item)
            for key, item in value.items()
            if str(key).lower() not in _FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return deepcopy(value)


def _required_string(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PilotModelHarnessError(f"missing_{name}")
    return text


def _validate_no_forbidden_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise PilotModelHarnessError(f"forbidden_key:{path}.{key}")
            _validate_no_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_forbidden_keys(item, f"{path}[{index}]")


def _tool_definitions(names: list[str]) -> list[dict[str, Any]]:
    if not isinstance(names, list) or not names:
        raise PilotModelHarnessError("pilot_must_supply_allowed_tools")
    unknown = sorted({str(name) for name in names} - set(GPT_OSS_PRIVATE_REASONING_TOOLS))
    if unknown:
        raise PilotModelHarnessError("unknown_or_unapproved_tool:" + ",".join(unknown))
    return [
        {"name": name, **deepcopy(GPT_OSS_PRIVATE_REASONING_TOOLS[name])}
        for name in names
    ]


def build_gpt_oss_private_reasoning_request(*, pilot_request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one Pilot-owned request into a GPT-OSS Harmony adapter request.

    The caller is expected to be an AION-selected Pilot.  This function does not
    select a Pilot, decide a business action, call a model, or invoke a tool.
    """
    _validate_no_forbidden_keys(pilot_request)
    pilot_id = _required_string(pilot_request.get("pilot_id"), "pilot_id")
    task_id = _required_string(pilot_request.get("task_id"), "task_id")
    business_id = _required_string(pilot_request.get("business_id"), "business_id")
    mission_id = _required_string(pilot_request.get("mission_id"), "mission_id")
    mission_run_id = _required_string(pilot_request.get("mission_run_id"), "mission_run_id")
    task = _required_string(pilot_request.get("task"), "task")
    output_schema = pilot_request.get("output_schema")
    if not isinstance(output_schema, Mapping) or not output_schema:
        raise PilotModelHarnessError("pilot_must_supply_output_schema")

    tools = _tool_definitions(pilot_request.get("allowed_tools"))
    facts = _redact(pilot_request.get("verified_business_facts", []))
    if not isinstance(facts, list):
        raise PilotModelHarnessError("verified_business_facts_must_be_list")

    contract = {
        "schema_version": HARNESS_SCHEMA,
        "harness_id": "gpt_oss_private_reasoning",
        "adapter": GPT_OSS_HARMONY_ADAPTER,
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "pilot_id": pilot_id,
        "task_id": task_id,
        "task": task,
        "verified_business_facts": facts,
        "output_schema": _redact(dict(output_schema)),
        "allowed_tools": tools,
        "limits": {
            "max_tool_proposals": int(pilot_request.get("max_tool_proposals", 3)),
            "max_output_tokens": int(pilot_request.get("max_output_tokens", 600)),
            "max_latency_ms": int(pilot_request.get("max_latency_ms", 30_000)),
        },
        # These are invariants, not preferences provided by the Pilot or model.
        "authority": {
            "aion_owns_routing": True,
            "pilot_owns_workflow": True,
            "harness_is_not_a_pilot": True,
            "model_may_propose": True,
            "model_may_execute": False,
            "model_may_mutate_business_memory": False,
            "model_may_call_raw_tools": False,
            "aion_gateway_must_validate_tool_proposals": True,
            "external_actions_require_existing_exact_approval": True,
        },
    }
    contract["contract_hash"] = _hash(contract)
    contract["adapter_request"] = {
        "format": "openai_harmony",
        "messages": _harmony_messages(contract),
        "stop_markers": ["<|return|>", "<|end|>"],
    }
    return contract


def _harmony_messages(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    developer = {
        "role": "developer",
        "content": (
            "You are a bounded reasoning coprocessor for an AION Pilot. "
            "AION owns routing, permissions, memory, approvals and tool execution. "
            "The Pilot owns this workflow. You may only return a final structured answer "
            "or propose one listed tool. Never claim a tool ran. Never send, publish, write "
            "records, expose hidden reasoning, or invent business facts."
        ),
    }
    task = {
        "task": contract["task"],
        "verified_business_facts": contract["verified_business_facts"],
        "output_schema": contract["output_schema"],
        "allowed_tools": contract["allowed_tools"],
        "limits": contract["limits"],
    }
    return [developer, {"role": "user", "content": _canonical(task)}]


def parse_gpt_oss_proposal(*, contract: Mapping[str, Any], model_text: str) -> dict[str, Any]:
    """Parse a returned Harmony-style model response into a non-executing event."""
    if contract.get("adapter") != GPT_OSS_HARMONY_ADAPTER:
        raise PilotModelHarnessError("unsupported_harness_adapter")
    response = str(model_text or "").strip()
    if not response:
        raise PilotModelHarnessError("empty_model_response")

    allowed_names = {item["name"] for item in contract.get("allowed_tools", [])}
    if "<|call|>" in response:
        payload_text = response.split("<|call|>", 1)[1].split("<|end|>", 1)[0].strip()
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise PilotModelHarnessError("invalid_harmony_tool_proposal_json") from exc
        if not isinstance(payload, Mapping):
            raise PilotModelHarnessError("harmony_tool_proposal_must_be_object")
        name = str(payload.get("name") or payload.get("tool") or "")
        arguments = payload.get("arguments", {})
        if name not in allowed_names:
            raise PilotModelHarnessError("tool_not_allowed_by_pilot:" + name)
        if not isinstance(arguments, Mapping):
            raise PilotModelHarnessError("tool_arguments_must_be_object")
        _validate_no_forbidden_keys(arguments, "tool_arguments")
        proposal = {
            "event_type": "tool_proposal",
            "tool_name": name,
            "arguments": _redact(dict(arguments)),
            "requires_aion_gateway": True,
            "tool_executed": False,
            "external_side_effect_executed": False,
        }
    else:
        final_text = response.split("<|return|>", 1)[-1].split("<|end|>", 1)[0].strip()
        proposal = {
            "event_type": "final_proposal",
            "content": final_text,
            "requires_aion_gateway": False,
            "tool_executed": False,
            "external_side_effect_executed": False,
        }

    event = {
        "schema_version": HARNESS_SCHEMA,
        "contract_hash": contract.get("contract_hash"),
        "pilot_id": contract.get("pilot_id"),
        "task_id": contract.get("task_id"),
        "proposal": proposal,
        "model_may_execute": False,
        "model_may_mutate_business_memory": False,
    }
    event["event_hash"] = _hash(event)
    return event


def create_harness_receipt(*, contract: Mapping[str, Any], event: Mapping[str, Any], elapsed_ms: int) -> dict[str, Any]:
    """Produce an observable receipt; it intentionally contains no hidden reasoning."""
    if event.get("contract_hash") != contract.get("contract_hash"):
        raise PilotModelHarnessError("event_contract_hash_mismatch")
    receipt = {
        "schema_version": "aion.pilot_model_harness_receipt.v1",
        "contract_hash": contract.get("contract_hash"),
        "event_hash": event.get("event_hash"),
        "business_id": contract.get("business_id"),
        "mission_id": contract.get("mission_id"),
        "mission_run_id": contract.get("mission_run_id"),
        "pilot_id": contract.get("pilot_id"),
        "task_id": contract.get("task_id"),
        "adapter": contract.get("adapter"),
        "event_type": event.get("proposal", {}).get("event_type"),
        "tool_name": event.get("proposal", {}).get("tool_name"),
        "elapsed_ms": int(elapsed_ms),
        "tool_executed": False,
        "external_side_effect_executed": False,
        "memory_mutated": False,
        "next_owner": "aion_tool_gateway" if event.get("proposal", {}).get("requires_aion_gateway") else "pilot",
    }
    receipt["receipt_hash"] = _hash(receipt)
    return receipt

QWEN3_NATIVE_TOOL_ADAPTER = "qwen3_native_tools.v1"


def build_qwen30_fast_local_request(*, pilot_request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a Pilot-owned bounded task for the Qwen3 native tool protocol.

    This contains no Qwen weight or runtime selection.  AION's model router and
    Vault preflight must choose a verified resident Qwen package separately.
    """
    _validate_no_forbidden_keys(pilot_request)
    pilot_id = _required_string(pilot_request.get("pilot_id"), "pilot_id")
    task_id = _required_string(pilot_request.get("task_id"), "task_id")
    business_id = _required_string(pilot_request.get("business_id"), "business_id")
    mission_id = _required_string(pilot_request.get("mission_id"), "mission_id")
    mission_run_id = _required_string(pilot_request.get("mission_run_id"), "mission_run_id")
    task = _required_string(pilot_request.get("task"), "task")
    output_schema = pilot_request.get("output_schema")
    if not isinstance(output_schema, Mapping) or not output_schema:
        raise PilotModelHarnessError("pilot_must_supply_output_schema")
    facts = _redact(pilot_request.get("verified_business_facts", []))
    if not isinstance(facts, list):
        raise PilotModelHarnessError("verified_business_facts_must_be_list")

    contract = {
        "schema_version": HARNESS_SCHEMA,
        "harness_id": "qwen30_fast_local",
        "adapter": QWEN3_NATIVE_TOOL_ADAPTER,
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "pilot_id": pilot_id,
        "task_id": task_id,
        "task": task,
        "verified_business_facts": facts,
        "output_schema": _redact(dict(output_schema)),
        "allowed_tools": _tool_definitions(pilot_request.get("allowed_tools")),
        "limits": {
            "max_tool_proposals": int(pilot_request.get("max_tool_proposals", 3)),
            "max_output_tokens": int(pilot_request.get("max_output_tokens", 400)),
            "max_latency_ms": int(pilot_request.get("max_latency_ms", 10_000)),
        },
        "authority": {
            "aion_owns_routing": True,
            "pilot_owns_workflow": True,
            "harness_is_not_a_pilot": True,
            "model_may_propose": True,
            "model_may_execute": False,
            "model_may_mutate_business_memory": False,
            "model_may_call_raw_tools": False,
            "aion_gateway_must_validate_tool_proposals": True,
            "external_actions_require_existing_exact_approval": True,
        },
    }
    contract["contract_hash"] = _hash(contract)
    task_envelope = {
        "task": task,
        "verified_business_facts": facts,
        "output_schema": contract["output_schema"],
        "allowed_tools": contract["allowed_tools"],
        "limits": contract["limits"],
    }
    contract["adapter_request"] = {
        "format": "qwen3_native_tool_calling",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bounded local coprocessor for an AION Pilot. "
                    "AION owns routing, permissions, memory, approvals and execution. "
                    "Return a final structured proposal, or one allowed tool proposal using "
                    "Qwen's <tool_call> JSON format. Never execute a tool or claim it ran."
                ),
            },
            {"role": "user", "content": _canonical(task_envelope)},
        ],
        "stop_markers": ["</tool_call>"],
    }
    return contract


def parse_qwen3_proposal(*, contract: Mapping[str, Any], model_text: str) -> dict[str, Any]:
    """Normalise Qwen's native <tool_call> JSON to an AION non-executing event."""
    if contract.get("adapter") != QWEN3_NATIVE_TOOL_ADAPTER:
        raise PilotModelHarnessError("unsupported_harness_adapter")
    response = str(model_text or "").strip()
    if not response:
        raise PilotModelHarnessError("empty_model_response")
    allowed_names = {item["name"] for item in contract.get("allowed_tools", [])}

    if "<tool_call>" in response:
        payload_text = response.split("<tool_call>", 1)[1].split("</tool_call>", 1)[0].strip()
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise PilotModelHarnessError("invalid_qwen_tool_proposal_json") from exc
        if not isinstance(payload, Mapping):
            raise PilotModelHarnessError("qwen_tool_proposal_must_be_object")
        name = str(payload.get("name") or payload.get("tool") or "")
        arguments = payload.get("arguments", payload.get("parameters", {}))
        if name not in allowed_names:
            raise PilotModelHarnessError("tool_not_allowed_by_pilot:" + name)
        if not isinstance(arguments, Mapping):
            raise PilotModelHarnessError("tool_arguments_must_be_object")
        _validate_no_forbidden_keys(arguments, "tool_arguments")
        proposal = {
            "event_type": "tool_proposal", "tool_name": name,
            "arguments": _redact(dict(arguments)), "requires_aion_gateway": True,
            "tool_executed": False, "external_side_effect_executed": False,
        }
    else:
        proposal = {
            "event_type": "final_proposal", "content": response,
            "requires_aion_gateway": False, "tool_executed": False,
            "external_side_effect_executed": False,
        }
    event = {
        "schema_version": HARNESS_SCHEMA, "contract_hash": contract.get("contract_hash"),
        "pilot_id": contract.get("pilot_id"), "task_id": contract.get("task_id"),
        "proposal": proposal, "model_may_execute": False,
        "model_may_mutate_business_memory": False,
    }
    event["event_hash"] = _hash(event)
    return event
