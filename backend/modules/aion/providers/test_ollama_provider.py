from backend.modules.aion.providers.ollama_provider import OllamaProvider


def main() -> None:
    provider = OllamaProvider()
    print("health ok:", provider.health().get("models", []))
    result = provider.generate(
        "Write one short sentence explaining what Aion Business is."
    )
    print(result.response)


if __name__ == "__main__":
    main()