"""
RepoForge V3 AI Fix Generator

Uses RepoForge provider system
to generate code improvements safely.
"""


from repoforge.providers.factory import ProviderFactory



class FixGenerator:
    """
    Generates fixed code using AI providers.
    """


    def __init__(
        self,
        model=None
    ):

        factory = ProviderFactory()


        self.provider = factory.create(
            model or "mock"
        )



    def generate_fix(
        self,
        file_path,
        content,
        issue
    ):
        """
        Generate complete updated file.

        Returns:
            Updated source code only.
        """


        prompt = f"""
You are a senior software engineer.

Fix the following issue.

File:
{file_path}


Issue:
{issue}


Current code:

{content}


Rules:
- Return only the complete fixed file
- No explanation
- No markdown
- Preserve existing functionality
- Do not remove working features
- Keep code production quality
"""


        try:

            response = self.provider.generate(
                prompt
            )


        except Exception:

            return ""



        if not response:

            return ""


        return response.strip()