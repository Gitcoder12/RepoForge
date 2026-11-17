"""Typed, safe errors exposed by real model providers."""


class ProviderError(RuntimeError):
    """Base class for provider setup and request failures."""


class ProviderConfigurationError(ProviderError):
    """The selected provider is not configured or its SDK is unavailable."""


class ProviderAuthenticationError(ProviderError):
    """The provider rejected the configured credentials."""


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request because of rate or quota limits."""


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the configured timeout."""


class ProviderConnectionError(ProviderError):
    """The provider endpoint could not be reached."""


class ProviderResponseError(ProviderError):
    """The provider returned an empty or unusable response."""


class ProviderRequestError(ProviderError):
    """The provider returned an unexpected request error."""
