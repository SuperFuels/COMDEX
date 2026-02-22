from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator
from backend.modules.aion_conversation.contracts import TurnPacket


def main() -> None:
    orch = ConversationOrchestrator()

    res = orch.handle_turn_packet(
        TurnPacket(
            session_id="kevin-contract-test",
            user_text="Explain what AION is building next.",
        )
    )

    print(type(res).__name__, res.mode, res.ok)
    print(sorted(res.to_dict().keys()))
    print("response:", res.response[:200])


if __name__ == "__main__":
    main()