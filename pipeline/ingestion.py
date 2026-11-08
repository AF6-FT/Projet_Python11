"""Lecture robuste des fichiers auth.log, y compris les archives gzip."""

import gzip
import zlib
from pathlib import Path
from typing import Iterator

from logger_config import get_logger

logger = get_logger(__name__)


def iter_log_lines(data_dir: Path) -> Iterator[tuple[Path, int, str]]:
    """Lit toutes les archives auth.log, sans passer par l'ingestion limitée."""
    data_dir = Path(data_dir)
    try:
        files = sorted(
            path
            for path in data_dir.iterdir()
            if path.is_file() and path.name.startswith("auth.log.")
        )
    except FileNotFoundError:
        logger.exception("Log data directory does not exist: %s", data_dir)
        raise
    except PermissionError:
        logger.exception("Permission denied while listing %s", data_dir)
        raise
    except OSError:
        logger.exception("Could not list log data directory %s", data_dir)
        raise

    if not files:
        error = FileNotFoundError(f"No auth.log files found in {data_dir}")
        logger.error("%s", error)
        raise error

    for path in files:
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rb") as stream:
                for line_number, raw_line in enumerate(stream, start=1):
                    try:
                        yield path, line_number, raw_line.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.exception(
                            "Invalid UTF-8 in %s at line %d", path, line_number
                        )
        except FileNotFoundError:
            logger.exception("Log file disappeared before it could be read: %s", path)
        except PermissionError:
            logger.exception("Permission denied while reading %s", path)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            logger.exception("Corrupted gzip log file: %s", path)
        except OSError:
            logger.exception("Could not read log file %s", path)
