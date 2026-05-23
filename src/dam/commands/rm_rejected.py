from __future__ import annotations

from pathlib import Path

import click


def rm_rejected(*, dry: bool, target_path: Path | None) -> None:
    raise click.ClickException("rm-rejected is not implemented in the Python port.")
