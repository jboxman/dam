from __future__ import annotations

import ctypes
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import click

from dam.config import DamConfig
from dam.external import log_message


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".heic"}


def _fail(message: str, path: Path) -> None:
    raise click.ClickException(f"{message}: {path}")


def _inventory(root: Path) -> dict[Path, Path]:
    def onerror(error: OSError) -> None:
        raise error

    files = {}
    for directory, dirs, names in os.walk(root, onerror=onerror, followlinks=False):
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                _fail("Directory symlinks are unsupported", path)
        for name in sorted(names):
            path = Path(directory) / name
            files[path.relative_to(root)] = path
    return files


def _destination(path: Path, root: Path) -> os.stat_result | None:
    for parent in reversed(path.relative_to(root).parents):
        directory = root / parent
        try:
            mode = directory.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(mode):
            _fail("Destination parent must be a real directory", directory)
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _regular(path: Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        _fail("Expected a regular file", path)
    return info


def _same(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _equal_contents(left: Path, right: Path) -> bool:
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            chunk = a.read(1024 * 1024)
            if chunk != b.read(1024 * 1024):
                return False
            if not chunk:
                return True


def _plan(source_root: Path, target_root: Path, file_sync: bool, meta_sync: bool):
    staging = _inventory(source_root)
    target = _inventory(target_root)
    actions = []
    if file_sync:
        for relative, source in staging.items():
            if source.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            resolved = source.resolve(strict=True)
            original = _regular(resolved)
            if original.st_mode & 0o222:
                _fail("Source image must already be read-only; sync never chmods originals", source)
            destination = target_root / relative
            existing = _destination(destination, target_root)
            clone_source = resolved
            if existing is not None:
                if stat.S_ISLNK(existing.st_mode):
                    if not destination.resolve(strict=True).samefile(resolved):
                        _fail("Unrelated target symlink", destination)
                elif stat.S_ISREG(existing.st_mode):
                    if existing.st_nlink == 1 and not _same(original, existing):
                        actions.append(("Ensure writable", destination, destination))
                        continue
                    clone_source = destination
                else:
                    _fail("Expected a regular target image", destination)
            actions.append(("Clone image", clone_source, destination))
    if meta_sync:
        # Validate all sidecars before writing, including retained staging files.
        for path in staging.values():
            if path.suffix.lower() == ".xmp" and _regular(path).st_nlink != 1:
                _fail("Hard-linked XMP destinations are unsupported", path)
        for relative, source in target.items():
            if source.suffix.lower() != ".xmp":
                continue
            _regular(source)
            destination = source_root / relative
            existing = _destination(destination, source_root)
            if existing is not None:
                if not stat.S_ISREG(existing.st_mode) or existing.st_nlink != 1:
                    _fail("XMP destination must be an ordinary single-link file", destination)
                if _equal_contents(source, destination):
                    continue
            actions.append(("Copy metadata", source, destination))
    return actions


def _clonefile(source: Path, destination: Path) -> None:
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    clone = library.clonefile
    clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clone.restype = ctypes.c_int
    if clone(os.fsencode(source), os.fsencode(destination), 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, f"clonefile {source} -> {destination}: {os.strerror(error)}; no fallback")


def _ensure_writable(path: Path) -> None:
    info = _regular(path)
    if info.st_nlink != 1:
        _fail("Refusing to chmod a shared inode", path)
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o600 != 0o600:
        path.chmod(mode | 0o600)
    with path.open("r+b"):
        pass


def _publish(source: Path, destination: Path, *, image: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".dam-sync-", dir=destination.parent) as folder:
        temporary = Path(folder) / "file"
        if image:
            _clonefile(source.resolve(strict=True), temporary)
            cloned = _regular(temporary)
            if _same(source.stat(), cloned):
                _fail("Clone unexpectedly shares its source inode", temporary)
            temporary.chmod(0o600)
            _ensure_writable(temporary)
        else:
            mode = stat.S_IMODE(destination.lstat().st_mode) if destination.exists() else 0o600
            with source.open("rb") as input_file, temporary.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file)
                output_file.flush()
                os.fsync(output_file.fileno())
            temporary.chmod(mode)
        os.replace(temporary, destination)


def sync(config: DamConfig, *, dry: bool, file_sync: bool, meta_sync: bool) -> None:
    if sys.platform != "darwin":
        raise click.ClickException("Sync requires macOS/APFS; no cloning fallback is supported.")
    if not file_sync and not meta_sync:
        file_sync = meta_sync = True
    try:
        source_root = config.staging_user_dir.resolve(strict=True)
        target_root = config.digikam_user_dir.resolve(strict=True)
        for root in (source_root, target_root):
            if not root.is_dir():
                _fail("Sync root must be an existing directory", root)
        if source_root == target_root or source_root in target_root.parents or target_root in source_root.parents:
            raise click.ClickException("Sync roots must be distinct and must not overlap.")
        actions = _plan(source_root, target_root, file_sync, meta_sync)
    except (OSError, RuntimeError) as exc:
        raise click.ClickException(f"Sync preflight failed: {exc}") from exc
    if dry:
        log_message("Dry run cannot verify clone support or effective destination writability.", dry=True)
    for operation, source, destination in actions:
        log_message(f"{operation}: {source} -> {destination}", dry=dry)
        if dry:
            continue
        try:
            if operation == "Ensure writable":
                _ensure_writable(destination)
            else:
                _publish(source, destination, image=operation == "Clone image")
        except (OSError, RuntimeError) as exc:
            raise click.ClickException(f"{operation} failed: {source} -> {destination}: {exc}") from exc
