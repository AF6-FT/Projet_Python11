"""Accès SQLite aux événements et au cache de géolocalisation."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from logger_config import get_logger
from storage.models import AuthEvent

logger = get_logger(__name__)


@contextmanager
def _connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Gère commit/rollback et ferme la connexion après chaque opération."""
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class EventStore:
    """Enregistre les événements SSH et les pays associés aux adresses IP."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Crée les tables nécessaires si elles n'existent pas."""
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with _connection(self.database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        ip TEXT NOT NULL,
                        username TEXT NOT NULL,
                        status TEXT NOT NULL CHECK (
                            status IN ('Success', 'Failed', 'Invalid')
                        ),
                        country TEXT NOT NULL,
                        attempts INTEGER NOT NULL CHECK (attempts > 0)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS country_cache (
                        ip TEXT PRIMARY KEY,
                        country TEXT NOT NULL
                    )
                    """
                )
        except (OSError, sqlite3.Error):
            logger.exception("Could not initialize database at %s", self.database_path)
            raise

    def replace_events(self, events: Iterable[AuthEvent]) -> None:
        """Remplace les événements pour rendre chaque exécution reproductible."""
        rows = [
            (
                event.timestamp,
                event.ip,
                event.username,
                event.status,
                event.country,
                event.attempts,
            )
            for event in events
        ]
        try:
            with _connection(self.database_path) as connection:
                connection.execute("DELETE FROM auth_events")
                connection.executemany(
                    """
                    INSERT INTO auth_events
                        (timestamp, ip, username, status, country, attempts)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        except sqlite3.Error:
            logger.exception("Could not replace authentication events")
            raise

    def get_country_cache(self) -> dict[str, str]:
        """Charge le cache persistant des pays."""
        try:
            with _connection(self.database_path) as connection:
                rows = connection.execute(
                    "SELECT ip, country FROM country_cache"
                ).fetchall()
            return {ip: country for ip, country in rows}
        except sqlite3.Error:
            logger.exception("Could not read the country cache")
            raise

    def save_country(self, ip: str, country: str) -> None:
        """Enregistre ou met à jour le pays d'une IP."""
        try:
            with _connection(self.database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO country_cache (ip, country) VALUES (?, ?)
                    ON CONFLICT(ip) DO UPDATE SET country = excluded.country
                    """,
                    (ip, country),
                )
        except sqlite3.Error:
            logger.exception("Could not cache country for IP %s", ip)
            raise

    def failed_attempts_by_country(self) -> list[tuple[str, int]]:
        """Retourne les échecs et utilisateurs invalides regroupés par pays."""
        query = """
            SELECT country, SUM(attempts) AS total
            FROM auth_events
            WHERE status IN ('Failed', 'Invalid')
            GROUP BY country
            ORDER BY total DESC, country
        """
        try:
            with _connection(self.database_path) as connection:
                return connection.execute(query).fetchall()
        except sqlite3.Error:
            logger.exception("Could not aggregate failed attempts by country")
            raise

    def successful_attempts_by_user(self) -> list[tuple[str, int]]:
        """Retourne les connexions réussies regroupées par utilisateur."""
        query = """
            SELECT username, SUM(attempts) AS total
            FROM auth_events
            WHERE status = 'Success'
            GROUP BY username
            ORDER BY total DESC, username
        """
        try:
            with _connection(self.database_path) as connection:
                return connection.execute(query).fetchall()
        except sqlite3.Error:
            logger.exception("Could not aggregate successful attempts by user")
            raise

    def invalid_user_attempts(self, limit: int) -> list[tuple[str, int]]:
        """Retourne les tentatives échouées pour des utilisateurs inconnus."""
        query = """
            SELECT username, SUM(attempts) AS total
            FROM auth_events
            WHERE status = 'Invalid'
            GROUP BY username
            ORDER BY total DESC, username
            LIMIT ?
        """
        try:
            with _connection(self.database_path) as connection:
                return connection.execute(query, (limit,)).fetchall()
        except sqlite3.Error:
            logger.exception("Could not aggregate invalid-user attempts")
            raise
