from repoforge.orchestrator import AIOrchestrator


def run_chat(prompt: str, model: str = None):

    orchestrator = AIOrchestrator()

    result = orchestrator.execute(
        prompt,
        model=model,
    )

    print(result)