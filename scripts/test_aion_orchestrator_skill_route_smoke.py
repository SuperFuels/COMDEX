from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator
from backend.modules.aion_conversation.contracts import TurnPacket


def main() -> None:
    orch = ConversationOrchestrator()

    # seed roadmap topic
    orch.handle_turn_packet(
        TurnPacket(
            session_id="kevin-c-orch",
            user_text="Explain what AION is building next.",
            include_debug=True,
        )
    )

    # trigger skill route (roadmap prioritization)
    res = orch.handle_turn_packet(
        TurnPacket(
            session_id="kevin-c-orch",
            user_text="prioritise the roadmap",
            include_debug=True,
        )
    )

    print(type(res).__name__, res.ok, res.mode)
    d = res.to_dict()
    print("has_skill_run:", "metadata" in d and "skill_run" in (d.get("metadata") or {}))
    print("response:", d.get("response"))
    if "debug" in d:
        print("debug_keys:", list(d["debug"].keys()))


if __name__ == "__main__":
    main()