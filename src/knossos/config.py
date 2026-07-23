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

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"

def get_paths() -> Paths:
    """Resolve Knossos's config/data/cache directories for the current OS,
    creating them if they don't exist yet."""
    config_dir = Path(_dirs.user_config_dir)
    data_dir = Path(_dirs.user_data_dir)
    cache_dir = Path(_dirs.user_cache_dir)

    for directory in (config_dir, data_dir, cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return Paths(config_dir=config_dir, data_dir=data_dir, cache_dir=cache_dir)

import toml


@dataclass
class Config:
    library_dir: str | None = None
    opds_root_url: str | None = None


def load_config(paths: Paths) -> Config:
    """
    Load user config from disk, falling back to defaults for any missing
    or absent fields. Never raises if the file doesn't exist yet, so a
    fresh install should just get an empty/default Config.
    """
    if not paths.config_file.exists():
        return Config()

    data = toml.load(paths.config_file)
    return Config(
        library_dir=data.get("library_dir"),
        opds_root_url=data.get("opds_root_url"),
    )


def save_config(paths: Paths, config: Config) -> None:
    """Write the given config to disk, overwriting any existing file."""
    data = {
        "library_dir": config.library_dir,
        "opds_root_url": config.opds_root_url,
    }
    # Drop keys with None values so an unset field doesn't get written as
    # `key = "None"` or similar, keeps the file clean for fields the user
    # hasn't configured yet.
    data = {k: v for k, v in data.items() if v is not None}

    with open(paths.config_file, "w") as f:
        toml.dump(data, f)
