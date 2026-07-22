# knossos/config.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "knossos"

_dirs = PlatformDirs(appname=APP_NAME, appauthor=False)


@dataclass(frozen=True)
class Paths:
    config_dir: Path
    data_dir: Path
    cache_dir: Path

    @property
    def db_file(self) -> Path:
        return self.data_dir / "knossos.db"


def get_paths() -> Paths:
    """Resolve Knossos's config/data/cache directories for the current OS,
    creating them if they don't exist yet."""
    config_dir = Path(_dirs.user_config_dir)
    data_dir = Path(_dirs.user_data_dir)
    cache_dir = Path(_dirs.user_cache_dir)

    for directory in (config_dir, data_dir, cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return Paths(config_dir=config_dir, data_dir=data_dir, cache_dir=cache_dir)
