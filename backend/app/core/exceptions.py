class ReviewError(Exception):
    """Base class for all review-pipeline errors."""


class ProviderDisabledError(ReviewError):
    """Raised when a provider is disabled via configuration."""


class ProviderUnavailableError(ReviewError):
    """Raised when a provider cannot be reached or times out."""


class ProviderResponseError(ReviewError):
    """Raised when a provider returns a response that fails validation."""


class AllProvidersExhaustedError(ReviewError):
    """Raised when every provider in the chain (including fallback) failed."""

    def __init__(self, attempts: list[str]):
        self.attempts = attempts
        super().__init__(f"All providers failed: {', '.join(attempts) or 'none attempted'}")


class CodeTooLargeError(ReviewError):
    """Raised when submitted code exceeds the configured size limit."""
