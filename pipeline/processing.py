"""Extraction des tentatives SSH sans modifier le module de cours existant."""

import ipaddress
import re
from datetime import datetime

from logger_config import get_logger
from storage.models import AuthEvent

logger = get_logger(__name__)

_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}
_HEADER = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+\S+\s+sshd(?:\[\d+\])?:\s*"
    r"(?P<message>.*)$"
)
_REPEATED = re.compile(
    r"^message repeated (?P<count>\d+) times:\s*\[(?P<message>.*)\]$",
    re.IGNORECASE,
)
_INVALID_USER = re.compile(
    r"^Invalid user\s*(?P<username>.*?)\s+from\s+"
    r"(?P<ip>\S+)\s+port\b"
)
_SUCCESS = re.compile(
    r"^Accepted \S+ for (?P<username>\S+) from (?P<ip>\S+)\s+port\b"
)
_FAILURE = re.compile(
    r"^Failed \S+ for (?:(?P<invalid>invalid|illegal) user"
    r"(?:\s+(?P<invalid_username>\S+))?|(?P<username>\S+))\s+"
    r"from (?P<ip>\S+)\s+port\b"
)


def parse_auth_line(
    line: str,
    source: str = "<input>",
    line_number: int = 0,
    year: int | None = None,
) -> AuthEvent | None:
    """Parse une ligne d'authentification; ignore les messages sans tentative."""
    header = _HEADER.match(line.rstrip("\r\n"))
    if header is None:
        if "sshd" in line and any(
            marker in line
            for marker in ("Accepted ", "Failed ", "Invalid user")
        ):
            logger.error("Unparseable SSH authentication line in %s:%d", source, line_number)
        return None

    message = header.group("message")
    attempts = 1
    repeated = _REPEATED.match(message)
    if repeated:
        attempts = int(repeated.group("count"))
        message = repeated.group("message")

    invalid_user = _INVALID_USER.match(message)
    success = _SUCCESS.match(message)
    failure = _FAILURE.match(message)
    match = invalid_user or success or failure
    if match is None:
        if message.startswith(("Accepted ", "Failed ", "Invalid user")):
            logger.error(
                "Unparseable SSH authentication message in %s:%d: %s",
                source,
                line_number,
                message,
            )
        return None

    ip = match.group("ip")
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        logger.error("Invalid IP address in %s:%d: %s", source, line_number, ip)
        return None

    month = _MONTHS.get(header.group("month"))
    if month is None:
        logger.error("Invalid month in %s:%d", source, line_number)
        return None
    try:
        parsed_date = datetime(
            year or datetime.now().year,
            month,
            int(header.group("day")),
            *map(int, header.group("time").split(":")),
        )
    except ValueError:
        logger.exception("Invalid timestamp in %s:%d", source, line_number)
        return None

    if invalid_user:
        username = invalid_user.group("username").strip() or "(vide)"
        status = "Invalid"
    else:
        username = (
            match.group("username")
            or match.group("invalid_username")
            or "(vide)"
        )
        status = "Success" if success else "Failed"
    return AuthEvent(
        timestamp=parsed_date.isoformat(sep=" "),
        ip=ip,
        username=username,
        status=status,
        attempts=max(attempts, 1),
    )
