"""Explicit standby routing for configured model providers.

Fallback is opt-in and limited to classified transient failures. Authentication,
configuration, and request errors stop immediately. This module never invents a
mock response or silently changes a provider outside the declared route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repoforge.providers.base import BaseProvider
from repoforge.providers.errors import (
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)


class ProviderFailoverExhaustedError(ProviderError):
    """Every explicitly configured candidate failed with a retryable error."""

    def __init__(self, attempts: tuple["ProviderAttempt", ...]) -> None:
        self.attempts = attempts
        summary = ", ".join(
            f"{attempt.provider_name}:{attempt.error_type or attempt.status}"
            for attempt in attempts
        )
        super().__init__(f"All configured model candidates failed ({summary}).")


@dataclass(frozen=True)
class ProviderAttempt:
    """Redacted metadata for one provider attempt; never stores prompts or keys."""

    provider_name: str
    model: str
    status: str
    error_type: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    """Response and auditable route metadata for one completed generation."""

    text: str
    provider_name: str
    model: str
    attempts: tuple[ProviderAttempt, ...]

    @property
    def used_standby(self) -> bool:
        return len(self.attempts) > 1


class StandbyProviderPool:
    """Run a primary model and explicitly configured standby candidates in order.

    By default only connection, timeout, and unusable-response failures trigger
    standby. Rate-limit fallback is opt-in because it may incur another provider
    charge. Authentication, configuration, request, and programming errors stop
    the route immediately.
    """

    def __init__(
        self,
        *,
        primary_name: str,
        providers: dict[str, BaseProvider],
        standby_names: tuple[str, ...] = (),
        allow_rate_limit_fallback: bool = False,
    ) -> None:
        if not isinstance(primary_name, str) or not primary_name.strip():
            raise ValueError("primary_name must be a non-empty string")
        if not isinstance(providers, dict) or not providers:
            raise ValueError("providers must be a non-empty mapping")
        if not isinstance(allow_rate_limit_fallback, bool):
            raise ValueError("allow_rate_limit_fallback must be a boolean")
        if not isinstance(standby_names, tuple):
            raise ValueError("standby_names must be a tuple")

        route = (primary_name.strip(),) + tuple(
            name.strip() for name in standby_names if isinstance(name, str)
        )
        if len(route) != len(standby_names) + 1:
            raise ValueError("standby provider names must be strings")
        if any(not name for name in route):
            raise ValueError("provider route names must be non-empty strings")
        if len(route) != len(set(route)):
            raise ValueError("provider route cannot contain duplicates")
        missing = [name for name in route if name not in providers]
        if missing:
            raise ValueError(
                f"provider route references unregistered providers: {', '.join(missing)}"
            )
        if any(not isinstance(providers[name], BaseProvider) for name in route):
            raise TypeError("every route candidate must implement BaseProvider")

        self.primary_name = route[0]
        self.route = route
        self.providers = {name: providers[name] for name in route}
        self.allow_rate_limit_fallback = allow_rate_limit_fallback

    @classmethod
    def from_factory(
        cls,
        *,
        primary_name: str,
        standby_names: tuple[str, ...] = (),
        model_overrides: dict[str, str] | None = None,
        timeout: float = 45.0,
        allow_rate_limit_fallback: bool = False,
        factory: Any = None,
    ) -> "StandbyProviderPool":
        """Build only the providers explicitly named by the caller or config."""
        if factory is None:
            from repoforge.providers.factory import ProviderFactory

            factory = ProviderFactory()
        overrides = model_overrides or {}
        names = (primary_name,) + tuple(standby_names)
        providers = {
            name: factory.get(
                name,
                model=overrides.get(name),
                timeout=timeout,
            )
            for name in names
        }
        return cls(
            primary_name=primary_name,
            providers=providers,
            standby_names=standby_names,
            allow_rate_limit_fallback=allow_rate_limit_fallback,
        )

    def _is_retryable(self, error: ProviderError) -> bool:
        transient = (
            ProviderConnectionError,
            ProviderTimeoutError,
            ProviderResponseError,
        )
        return isinstance(error, transient) or (
            self.allow_rate_limit_fallback and isinstance(error, ProviderRateLimitError)
        )

    @staticmethod
    def _model_name(provider: BaseProvider) -> str:
        models = provider.models
        return str(models[0]) if models else "unspecified"

    def generate_with_report(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate through the route and return redacted attempt metadata."""
        attempts: list[ProviderAttempt] = []
        for index, name in enumerate(self.route):
            provider = self.providers[name]
            model = self._model_name(provider)
            try:
                text = provider.generate(prompt, system_prompt=system_prompt, **kwargs)
            except ProviderError as exc:
                attempts.append(
                    ProviderAttempt(
                        provider_name=name,
                        model=model,
                        status="failed",
                        error_type=type(exc).__name__,
                    )
                )
                if not self._is_retryable(exc):
                    raise
                if index == len(self.route) - 1:
                    raise ProviderFailoverExhaustedError(tuple(attempts)) from exc
                continue

            if not isinstance(text, str) or not text.strip():
                attempts.append(
                    ProviderAttempt(
                        provider_name=name,
                        model=model,
                        status="failed",
                        error_type="InvalidProviderResponse",
                    )
                )
                if index == len(self.route) - 1:
                    raise ProviderFailoverExhaustedError(tuple(attempts))
                continue

            attempts.append(ProviderAttempt(provider_name=name, model=model, status="success"))
            return GenerationResult(
                text=text,
                provider_name=name,
                model=model,
                attempts=tuple(attempts),
            )

        raise ProviderFailoverExhaustedError(tuple(attempts))

    def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        """Return only response text for callers that do not need route metadata."""
        return self.generate_with_report(prompt, system_prompt, **kwargs).text
