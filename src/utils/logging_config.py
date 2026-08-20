import logging
from pathlib import Path


def setup_logging(log_file: str = "data/tennis_tracker.log", level: int = logging.INFO) -> None:
    """Configure console + file logging once, so scheduled/unattended runs leave a record."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
