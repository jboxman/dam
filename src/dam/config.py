from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, Mapping


@dataclass
class PhotographerConfig:
    copyrightArgs: str


@dataclass
class DamConfig:
    defaultUser: str
    stagingDir: str
    digikamDir: str
    photographers: Dict[str, PhotographerConfig] = field(default_factory=dict)

    @property
    def staging_user_dir(self) -> Path:
        return Path(self.stagingDir) / self.defaultUser

    @property
    def digikam_user_dir(self) -> Path:
        return Path(self.digikamDir) / self.defaultUser

    def copyright_args_for_user(self, user: str | None = None) -> Path:
        selected_user = user or self.defaultUser
        try:
            return Path(self.photographers[selected_user].copyrightArgs)
        except KeyError as exc:
            raise KeyError(f"Missing photographer config for user {selected_user!r}") from exc


def config_dir(home: str | None = None) -> Path:
    home_dir = Path(home or os.environ["HOME"])
    return home_dir / ".dam"


def config_file(home: str | None = None) -> Path:
    return config_dir(home) / "config.json"


def exiftool_config_file(home: str | None = None) -> Path:
    return config_dir(home) / "exiftool.conf"


def default_config(env: Mapping[str, str] | None = None) -> DamConfig:
    environ = dict(os.environ if env is None else env)
    default_user = environ.get("USER") or Path(environ.get("HOME", str(Path.home()))).name
    home_dir = Path(environ.get("HOME", str(Path.home())))
    dam_dir = home_dir / ".dam"
    return DamConfig(
        defaultUser=default_user,
        stagingDir=str(home_dir / "Self/repos/photos/photographers"),
        digikamDir=str(home_dir / "Self/repos/photos-dk/photographers"),
        photographers={
            default_user: PhotographerConfig(
                copyrightArgs=str(dam_dir / f"{default_user}-copyright.conf")
            )
        },
    )


def _merge_raw(defaults: DamConfig, override: Mapping[str, object]) -> DamConfig:
    photographers: Dict[str, PhotographerConfig] = dict(defaults.photographers)
    for user, values in dict(override.get("photographers", {})).items():
        current = photographers.get(user, PhotographerConfig(copyrightArgs=""))
        if isinstance(values, Mapping):
            photographers[user] = PhotographerConfig(
                copyrightArgs=str(values.get("copyrightArgs", current.copyrightArgs))
            )

    return DamConfig(
        defaultUser=str(override.get("defaultUser", defaults.defaultUser)),
        stagingDir=str(override.get("stagingDir", defaults.stagingDir)),
        digikamDir=str(override.get("digikamDir", defaults.digikamDir)),
        photographers=photographers,
    )


def load_config(home: str | None = None, env: Mapping[str, str] | None = None) -> DamConfig:
    defaults = default_config(env=env)
    path = config_file(home or (env or {}).get("HOME"))
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError:
        raw = {}
    return _merge_raw(defaults, raw)


def prepare_config(home: str | None = None) -> None:
    destination_dir = config_dir(home)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = exiftool_config_file(home)
    if destination.exists():
        return
    resource = resources.files("dam.resources").joinpath("exiftool.conf")
    destination.write_text(resource.read_text())
