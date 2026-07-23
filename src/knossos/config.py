# knossos/config.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import PlatformDirs

import toml

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




@dataclass
class OPDSServerConfig:
    url: str
    name: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.url



@dataclass
class Config:
    library_dirs: list[str] = field(default_factory=list)  # was library_dir: str | None
    opds_servers: list[OPDSServerConfig] = field(default_factory=list)
    opds_root_url: str | None = None
    theme: str | None = None
    max_width: int | None = None


def load_config(paths: Paths) -> Config:
    if not paths.config_file.exists():
        return Config()

    data = toml.load(paths.config_file)

    library_dirs = data.get("library_dirs")
    if library_dirs is None:
        legacy_single_dir = data.get("library_dir")
        library_dirs = [legacy_single_dir] if legacy_single_dir else []

    # Backward compatibility: migrate old singular opds_root_url into the
    # new opds_servers list, giving it no nickname (falls back to showing
    # the URL itself in any server picker).
    raw_servers = data.get("opds_servers")
    if raw_servers is not None:
        opds_servers = [OPDSServerConfig(url=s["url"], name=s.get("name")) for s in raw_servers]
    else:
        legacy_url = data.get("opds_root_url")
        opds_servers = [OPDSServerConfig(url=legacy_url)] if legacy_url else []

    return Config(
        library_dirs=library_dirs,
        opds_servers=opds_servers,
        theme=data.get("theme"),
        max_width=data.get("max_width"),
    )

def save_config(paths: Paths, config: Config) -> None:
    data = {
        "library_dirs": config.library_dirs,
        "opds_servers": [
            {"url": s.url, **({"name": s.name} if s.name else {})}
            for s in config.opds_servers
        ],
        "theme": config.theme,
        "max_width": config.max_width,
    }
    data = {k: v for k, v in data.items() if v is not None and v != []}

    with open(paths.config_file, "w") as f:
        toml.dump(data, f)
