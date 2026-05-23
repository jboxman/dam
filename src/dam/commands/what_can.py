from __future__ import annotations

from pathlib import Path

import click

from dam.paths import iter_files, require_directory


ACTIONS = {
    "ROTATE": ".rotate",
    "COPYRIGHT": ".copyright",
    "INGEST": ".ingest",
    "CLEAN": ".clean",
}


def what_can(photo_dir: Path) -> None:
    try:
        require_directory(photo_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise click.ClickException(str(exc)) from exc

    dots = {path.name for path in iter_files(photo_dir) if path.name.startswith(".")}
    if all(marker in dots for marker in ACTIONS.values()):
        click.echo("[RUN] All valid actions for an import dir are complete.")
        return

    available = [name for name, marker in ACTIONS.items() if marker not in dots]
    click.echo(f"[RUN] Available actions: {', '.join(available)}")
