from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def marker_exists(photo_dir: Path, marker: str) -> bool:
    return (photo_dir / f".{marker}").exists()


def require_directory(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Expected directory: {path}")


def iter_files(path: Path) -> Iterator[Path]:
    return (item for item in path.rglob("*") if item.is_file())


def relative_map(files: Iterable[Path], root: Path) -> dict[Path, Path]:
    return {file.relative_to(root): file for file in files}
