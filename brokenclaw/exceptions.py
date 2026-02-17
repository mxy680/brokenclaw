class AuthenticationError(Exception):
    """Raised when OAuth credentials are missing or invalid."""


class IntegrationError(Exception):
    """Raised when an external API call fails."""


class RateLimitError(Exception):
    """Raised when an external API rate limit is hit."""
