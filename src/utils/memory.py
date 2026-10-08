import json
from pathlib import Path


class AIMemory:
    """
    Simple persistent memory for RepoForge.
    """

    def __init__(self):

        self.memory_dir = Path("memory/sessions")
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.file = self.memory_dir / "latest.json"

    def save(self, prompt, results):

        data = {

            "prompt": prompt,
            "results": results,

        }

        with open(self.file, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
            )

    def load(self):

        if not self.file.exists():

            return None

        with open(self.file, "r", encoding="utf-8") as f:

            return json.load(f)

    def has_memory(self):

        return self.file.exists()

    def clear(self):

        if self.file.exists():

            self.file.unlink()


if __name__ == "__main__":

    memory = AIMemory()

    memory.save(

        "Build Netflix clone",

        [

            {

                "task": "backend",

                "response": "Completed."

            }

        ]

    )

    print(memory.load())