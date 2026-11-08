"""Enrichissement, stockage et exécution complète du pipeline."""

import ipaddress
from dataclasses import replace
from pathlib import Path

import requests

from logger_config import get_logger
from pipeline.ingestion import iter_log_lines
from pipeline.processing import parse_auth_line
from storage.database import EventStore
from storage.models import AuthEvent

logger = get_logger(__name__)
_INGESTION_LOGGER = get_logger("pipeline.ingestion")
_PROCESSING_LOGGER = get_logger("pipeline.processing")
_IPINFO_URL = "https://ipinfo.io/{ip}/json"


def _lookup_country(ip: str) -> str | None:
    """Interroge ipinfo avec un timeout explicite; retourne None en cas d'échec."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        _PROCESSING_LOGGER.error("Invalid IP address skipped during geolocation: %s", ip)
        return "Unknown"

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    ):
        return "Unknown"

    try:
        response = requests.get(_IPINFO_URL.format(ip=ip), timeout=(3.05, 8))
    except requests.exceptions.Timeout:
        logger.exception("Geolocation timed out for IP %s", ip)
        return None
    except requests.exceptions.RequestException:
        logger.exception("Geolocation request failed for IP %s", ip)
        return None

    if response.status_code != 200:
        logger.error(
            "ipinfo returned HTTP %d for IP %s", response.status_code, ip
        )
        return None

    try:
        country = response.json().get("country")
    except (ValueError, AttributeError):
        logger.exception("Invalid ipinfo response for IP %s", ip)
        return None
    if not isinstance(country, str) or not country.strip():
        logger.error("ipinfo response has no country for IP %s", ip)
        return None
    return country.strip().upper()


def run_pipeline(data_dir: Path, store: EventStore) -> list[AuthEvent]:
    """Parse tous les journaux, géolocalise les IP et remplace les événements."""
    store.initialize()
    events: list[AuthEvent] = []
    for path, line_number, line in iter_log_lines(data_dir):
        event = parse_auth_line(line, str(path), line_number)
        if event is not None:
            events.append(event)

    country_cache = store.get_country_cache()
    resolved: dict[str, str] = dict(country_cache)
    for index, event in enumerate(events):
        if event.ip not in resolved:
            country = _lookup_country(event.ip)
            resolved[event.ip] = country or "Unknown"
            if country is not None:
                store.save_country(event.ip, country)
        events[index] = replace(event, country=resolved[event.ip])

    store.replace_events(events)
    _INGESTION_LOGGER.info("Parsed %d authentication log events", len(events))
    logger.info("Pipeline completed with %d events", len(events))
    return events
