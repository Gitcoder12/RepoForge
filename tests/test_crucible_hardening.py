from __future__ import annotations

import asyncio

from repoforge.providers.mock import MockProvider
from repoforge.security.crucible import Crucible


def test_generate_redacts_secrets_from_both_prompt_channels():
    wrapped = MockProvider("safe response")
    guarded = Crucible(wrapped)

    result = guarded.generate(
        "user has sk-abcdefghijklmnopqrstuvwxyz0123456789",
        "system credential sk-ant-abcdefghijklmnopqrstuvwxyz0123456789",
    )

    assert result == "safe response"
    assert wrapped.calls[0]["prompt"] == "user has [REDACTED_BY_CRUCIBLE]"
    assert wrapped.calls[0]["system_prompt"] == "system credential [REDACTED_BY_CRUCIBLE]"


class ChunkedMockProvider(MockProvider):
    def __init__(self, chunks: list[str]):
        super().__init__("unused")
        self.chunks = chunks

    async def stream(self, prompt: str, system_prompt: str = "", **kwargs):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        for chunk in self.chunks:
            yield chunk


def test_stream_blocks_dangerous_pattern_split_across_chunks():
    guarded = Crucible(ChunkedMockProvider(["safe preface; rm -rf ", "/"]))

    result = asyncio.run(_collect(guarded.stream("prompt")))

    assert result == ["ERROR: Stream blocked by Crucible."]


def test_stream_buffers_safe_chunks_and_redacts_system_prompt():
    wrapped = ChunkedMockProvider(["safe ", "and ", "sound"])
    guarded = Crucible(wrapped)

    result = asyncio.run(
        _collect(
            guarded.stream(
                "prompt",
                "system secret sk-abcdefghijklmnopqrstuvwxyz0123456789",
            )
        )
    )

    assert result == ["safe ", "and ", "sound"]
    assert wrapped.calls[0]["system_prompt"] == "system secret [REDACTED_BY_CRUCIBLE]"


def test_stream_blocks_response_over_inspection_limit():
    wrapped = ChunkedMockProvider(["x" * (Crucible.MAX_STREAM_INSPECTION_BYTES + 1)])
    guarded = Crucible(wrapped)

    result = asyncio.run(_collect(guarded.stream("prompt")))

    assert result == ["ERROR: Stream blocked by Crucible due to inspection size limit."]


async def _collect(stream):
    return [chunk async for chunk in stream]
