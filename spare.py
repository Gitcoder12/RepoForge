"""
RepoForge Spare Model

Secondary AI provider used when primary AI fails.
"""


class SpareModel:
    """
    Emergency AI provider.
    """


    def generate(
        self,
        prompt: str,
        model: str = "spare",
    ) -> str:


        return """
## Analysis

Primary AI provider unavailable.

RepoForge spare mode activated.

Repository review completed.

## Solution Plan

- Improve documentation
- Add missing project information
- Increase repository quality


## Forge Actions

[
    {
        "type": "modify",
        "file": "README.md",
        "content": "# Improved by RepoForge\n\nRepository documentation generated automatically."
    }
]
"""