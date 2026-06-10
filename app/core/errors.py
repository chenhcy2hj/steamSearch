class SteamSearchError(Exception):
    """Base exception for SteamSearch."""


class ConfigError(SteamSearchError):
    """Raised when configuration is invalid."""


class DatabaseError(SteamSearchError):
    """Raised when database initialization or access fails."""


class ExternalApiError(SteamSearchError):
    """Raised when an external API call fails."""


class AuthError(ExternalApiError):
    """Raised when an external API rejects credentials."""


class RateLimitError(ExternalApiError):
    """Raised when an external API rate limit is reached."""


class DataParseError(ExternalApiError):
    """Raised when an external API response cannot be parsed."""

