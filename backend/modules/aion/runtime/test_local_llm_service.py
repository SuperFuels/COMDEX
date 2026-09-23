from backend.modules.aion.runtime.services.local_llm_service import LocalLLMService


def main() -> None:
    service = LocalLLMService()

    health = service.health()
    print(
        "health:",
        {
            "ok": health.ok,
            "enabled": health.enabled,
            "model": health.model,
            "base_url": health.base_url,
            "payload": health.payload,
        },
    )

    result = service.generate(
        prompt="Summarise what a plumbing business does in one sentence."
    )
    print("result:", result.response)
    print("provider:", result.provider)
    print("model:", result.model)
    print("done:", result.done)
    print("done_reason:", result.done_reason)


if __name__ == "__main__":
    main()