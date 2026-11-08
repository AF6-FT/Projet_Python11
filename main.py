
import sqlite3

from logger_config import PROJECT_DIR, get_logger
from pipeline.orchestrator import run_pipeline
from serving.dashboard import build_dashboard
from storage.database import EventStore

logger = get_logger(__name__)


def main() -> None:
    """Exécute le pipeline puis crée le tableau de bord."""
    store = EventStore(PROJECT_DIR / "storage" / "ssh_events.sqlite3")
    try:
        run_pipeline(PROJECT_DIR / "data", store)
        build_dashboard(store, PROJECT_DIR / "output")
    except (OSError, sqlite3.Error, ValueError, RuntimeError):
        logger.exception("Pipeline stopped because of an application error")
        raise


if __name__ == "__main__":
    main()
    