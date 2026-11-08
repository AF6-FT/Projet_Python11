"""Structures de données utilisées par le stockage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthEvent:
    """Une tentative d'authentification extraite des journaux SSH."""

    timestamp: str
    ip: str
    username: str
    status: str
    country: str = "Unknown"
    attempts: int = 1
