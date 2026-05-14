from backend.modules.aion.runtime.services.local_llm_tasks import LocalLLMTasks


def main() -> None:
    tasks = LocalLLMTasks()

    summary = tasks.summarize(
        "A plumbing business installs, repairs, and maintains pipes, drains, fittings, "
        "water heaters, and sanitation systems for homes and businesses."
    )
    print("summary:", summary.output)

    draft = tasks.draft_reply(
        "Hi, can you send me a quote for fixing a leaking bathroom pipe?",
        tone="friendly and professional",
        purpose="acknowledge the request and ask for the details needed to quote",
    )
    print("draft:", draft.output)


if __name__ == "__main__":
    main()