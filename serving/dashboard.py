"""Création du tableau de bord des tentatives SSH."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from logger_config import get_logger
from storage.database import EventStore

logger = get_logger(__name__)


def _draw_bars(axis: Axes, labels: list[str], values: list[int]) -> None:
    """Dessine un histogramme horizontal lisible, y compris sans résultats."""
    if not labels:
        axis.text(0.5, 0.5, "Aucune donnée", ha="center", va="center")
        axis.set_axis_off()
        return
    bars = axis.barh(labels[::-1], values[::-1], color="#3478c8")
    axis.bar_label(bars, padding=4, fontsize=8)
    axis.grid(axis="x", alpha=0.25)
    axis.set_axisbelow(True)


def build_dashboard(
    store: EventStore,
    output_dir: Path,
    top_n: int = 15,
    show: bool = True,
) -> Path:
    """Affiche et sauvegarde les trois graphiques dans une seule fenêtre."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    output_dir = Path(output_dir)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.exception("Could not create dashboard output directory %s", output_dir)
        raise

    figure: Figure | None = None
    try:
        countries = store.failed_attempts_by_country()[:top_n]
        users = store.successful_attempts_by_user()[:top_n]
        invalid_users = store.invalid_user_attempts(top_n)

        figure = plt.figure(figsize=(16, 10), constrained_layout=True)
        grid = figure.add_gridspec(2, 2)
        country_axis = figure.add_subplot(grid[0, 0])
        success_axis = figure.add_subplot(grid[0, 1])
        invalid_axis = figure.add_subplot(grid[1, :])

        _draw_bars(
            country_axis,
            [country or "Unknown" for country, _ in countries],
            [total for _, total in countries],
        )
        country_axis.set_title(f"1. Tentatives échouées par pays (top {top_n})")
        country_axis.set_xlabel("Nombre de tentatives")
        country_axis.set_ylabel("Pays (code ISO)")

        _draw_bars(
            success_axis,
            [username or "(vide)" for username, _ in users],
            [total for _, total in users],
        )
        success_axis.set_title("2. Connexions réussies par utilisateur")
        success_axis.set_xlabel("Nombre de connexions réussies")
        success_axis.set_ylabel("Utilisateur")

        _draw_bars(
            invalid_axis,
            [username or "(vide)" for username, _ in invalid_users],
            [total for _, total in invalid_users],
        )
        invalid_axis.set_title(
            f"3. Tentatives échouées avec 'Invalid user' (top {top_n})"
        )
        invalid_axis.set_xlabel("Nombre de tentatives")
        invalid_axis.set_ylabel("Nom d'utilisateur invalide")

        figure.suptitle("Analyse des logs SSH (auth.log)", fontsize=16, fontweight="bold")
        output_path = output_dir / "ssh_dashboard.png"
        figure.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info("Dashboard saved to %s", output_path)
        if show:
            plt.show()
        return output_path
    except OSError:
        logger.exception("Could not write dashboard to %s", output_dir)
        raise
    except (RuntimeError, ValueError):
        logger.exception("Could not build SSH dashboard")
        raise
    finally:
        if figure is not None:
            plt.close(figure)
