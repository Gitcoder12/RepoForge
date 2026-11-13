"""Provider wrapper that redacts common secrets and blocks dangerous output."""

import logging
import re
from typing import Any, AsyncGenerator

from repoforge.base import BaseProvider

logger = logging.getLogger("RepoForge.Security.Crucible")


class Crucible(BaseProvider):
    def __init__(self, wrapped_provider: BaseProvider) -> None:
        self.wrapped = wrapped_provider
        super().__init__(api_key=self.wrapped.api_key, **self.wrapped.config)
        self.secret_patterns = (
            (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key"),
            (r"sk-ant-[a-zA-Z0-9]{32,}", "Anthropic API Key"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Token"),
            (r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key"),
        )
        self.malicious_response_patterns = (
            r"rm\s+-rf\s+/",
            r"curl\s+.*\|\s*bash",
            r"wget\s+.*\|\s*sh",
            r"eval\s*\(\s*base64",
        )

    def _initialize(self) -> None:
        return None

    def _sanitize_outbound(self, text: str) -> str:
        sanitized = text
        for pattern, secret_name in self.secret_patterns:
            if re.search(pattern, sanitized):
                logger.warning("Crucible redacted %s", secret_name)
                sanitized = re.sub(pattern, "[REDACTED_BY_CRUCIBLE]", sanitized)
        return sanitized

    def _inspect_inbound(self, text: str) -> bool:
        return not any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in self.malicious_response_patterns
        )

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        safe_prompt = self._sanitize_outbound(prompt)
        response = self.wrapped.generate(safe_prompt, system_prompt, **kwargs)
        if not self._inspect_inbound(response):
            return "ERROR: Response blocked by RepoForge Crucible due to malicious content."
        return response

    async def stream(
        self, prompt: str, system_prompt: str = "", **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        safe_prompt = self._sanitize_outbound(prompt)
        async for chunk in self.wrapped.stream(safe_prompt, system_prompt, **kwargs):
            if not self._inspect_inbound(chunk):
                yield "ERROR: Stream blocked by Crucible."
                break
            yield chunk

    def get_capabilities(self) -> dict[str, Any]:
        return self.wrapped.get_capabilities()

    def available(self) -> bool:
        return self.wrapped.available()

    @property
    def name(self) -> str:
        return f"Crucible({self.wrapped.name})"

    @property
    def models(self) -> list:
        return self.wrapped.models
