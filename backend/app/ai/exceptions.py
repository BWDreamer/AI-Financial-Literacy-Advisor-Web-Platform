class LLMConfigurationError(Exception):
    """Raised when the configured LLM provider cannot be used."""


class LLMServiceError(Exception):
    """Raised when the LLM provider fails to generate a response."""
