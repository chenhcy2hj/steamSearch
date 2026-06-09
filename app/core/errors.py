class SteamSearchError(Exception):
    """Base exception for SteamSearch."""


class ConfigError(SteamSearchError):
    """Raised when configuration is invalid."""


class DatabaseError(SteamSearchError):
    """Raised when database initialization or access fails."""

