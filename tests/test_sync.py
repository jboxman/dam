import errno
import importlib
import os
import stat

import click
import pytest
from click.testing import CliRunner

from dam.cli import cli
from dam.config import DamConfig

module = importlib.import_module("dam.commands.sync")


@pytest.fixture
def roots(tmp_path):
    config = DamConfig("tester", str(tmp_path / "staging"), str(tmp_path / "target"))
    config.staging_user_dir.mkdir(parents=True)
    config.digikam_user_dir.mkdir(parents=True)
    return config, config.staging_user_dir, config.digikam_user_dir


def run(config, **kwargs):
    module.sync(config, dry=kwargs.pop("dry", False),
                file_sync=kwargs.pop("file_sync", False),
                meta_sync=kwargs.pop("meta_sync", False), **kwargs)


def image(path):
    path.write_bytes(b"original image")
    path.chmod(0o444)
    return path


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        content = os.readlink(path) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        result[str(path.relative_to(root))] = (info.st_mode, info.st_mtime_ns, content)
    return result


@pytest.mark.parametrize("kind", ["new", "annex", "hardlink", "symlink", "other-hardlink"])
def test_real_clone_isolation_and_repeat(roots, tmp_path, kind):
    config, staging, target = roots
    source = image(staging / "a.jpg")
    destination = target / "a.jpg"
    backing = source
    if kind == "annex":
        backing = tmp_path / "object"
        source.rename(backing)
        source.symlink_to(backing)
    elif kind == "hardlink":
        os.link(source, destination)
    elif kind == "symlink":
        destination.symlink_to(source)
    elif kind == "other-hardlink":
        other = tmp_path / "other.jpg"
        other.write_bytes(b"target edits")
        os.link(other, destination)
    expected = b"target edits" if kind == "other-hardlink" else backing.read_bytes()
    before = (backing.read_bytes(), stat.S_IMODE(backing.stat().st_mode))
    run(config)
    assert not destination.is_symlink()
    assert not destination.samefile(backing)
    assert destination.stat().st_nlink == 1
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert destination.read_bytes() == expected
    with destination.open("r+b") as handle:
        handle.write(b"EDIT")
    destination.chmod(0o640)
    edited = destination.read_bytes()
    run(config)
    assert destination.read_bytes() == edited
    assert (backing.read_bytes(), stat.S_IMODE(backing.stat().st_mode)) == before
    if kind == "other-hardlink":
        assert other.read_bytes() == b"target edits"


def test_missing_root_preserves_sidecars(roots):
    config, staging, target = roots
    sidecar = staging / "a.xmp"
    sidecar.write_text("keep")
    target.rmdir()
    with pytest.raises(click.ClickException, match="preflight"):
        run(config)
    assert sidecar.read_text() == "keep"
    assert not target.exists()


@pytest.mark.parametrize("problem", ["dangling", "writable", "directory-link", "parent-file", "unrelated-link", "special"])
def test_preflight_makes_no_changes(roots, tmp_path, problem):
    config, staging, target = roots
    image(staging / "first.jpg")
    if problem == "dangling":
        (staging / "bad.jpg").symlink_to(tmp_path / "missing")
        (target / "bad.jpg").write_bytes(b"only copy")
    elif problem == "writable":
        (staging / "bad.jpg").write_text("writable")
    elif problem == "directory-link":
        (target / "escape").symlink_to(staging, target_is_directory=True)
    elif problem == "parent-file":
        (staging / "nested").mkdir()
        image(staging / "nested/a.jpg")
        (target / "nested").write_text("obstruction")
    elif problem == "unrelated-link":
        other = image(tmp_path / "other.jpg")
        (target / "first.jpg").symlink_to(other)
    else:
        os.mkfifo(staging / "bad.jpg")
    before = snapshot(tmp_path)
    with pytest.raises(click.ClickException):
        run(config)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("overlap", ["same", "nested"])
def test_overlapping_roots(roots, overlap):
    config, staging, target = roots
    if overlap == "same":
        config.digikamDir = config.stagingDir
    else:
        config.digikamDir = str(staging)
        (staging / config.defaultUser).mkdir()
    with pytest.raises(click.ClickException, match="overlap"):
        run(config)


def test_walk_error_is_not_empty_inventory(roots, monkeypatch):
    config, staging, target = roots
    def broken_walk(root, *, onerror, followlinks):
        onerror(PermissionError(errno.EACCES, "scan denied", str(root)))
        return iter(())
    monkeypatch.setattr(module.os, "walk", broken_walk)
    with pytest.raises(click.ClickException, match="scan denied"):
        run(config)


@pytest.mark.parametrize("problem", ["input-link", "destination-link", "destination-hardlink"])
def test_unsafe_xmp_aborts_image_creation(roots, tmp_path, problem):
    config, staging, target = roots
    image(staging / "a.jpg")
    backing = tmp_path / "object"
    backing.write_text("old")
    if problem == "input-link":
        (target / "a.xmp").symlink_to(backing)
    else:
        (target / "a.xmp").write_text("new")
        if problem == "destination-link":
            (staging / "a.xmp").symlink_to(backing)
        else:
            os.link(backing, staging / "a.xmp")
    before = snapshot(tmp_path)
    with pytest.raises(click.ClickException):
        run(config)
    assert snapshot(tmp_path) == before


def test_metadata_atomic_update_mode_and_unchanged_skip(roots):
    config, staging, target = roots
    source = target / "a.xmp"
    destination = staging / "a.xmp"
    source.write_text("new")
    destination.write_text("old")
    destination.chmod(0o440)
    with destination.open("rb") as old:
        run(config, meta_sync=True)
        assert old.read() == b"old"
    assert destination.read_text() == "new"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o440
    before = destination.stat()
    run(config, meta_sync=True)
    assert destination.stat().st_ino == before.st_ino
    assert destination.stat().st_mtime_ns == before.st_mtime_ns
    (target / "new.xmp").write_text("brand new")
    run(config, meta_sync=True)
    assert stat.S_IMODE((staging / "new.xmp").stat().st_mode) == 0o600


@pytest.mark.parametrize("failure", ["copy", "fsync", "replace"])
def test_metadata_failure_preserves_old_file(roots, monkeypatch, failure):
    config, staging, target = roots
    (target / "a.xmp").write_text("new")
    destination = staging / "a.xmp"
    destination.write_text("old")
    def fail(*args, **kwargs):
        if failure == "copy":
            args[1].write(b"partial")
        raise OSError(errno.EIO, "injected failure")
    if failure == "copy":
        monkeypatch.setattr(module.shutil, "copyfileobj", fail)
    else:
        monkeypatch.setattr(module.os, failure, fail)
    with pytest.raises(click.ClickException, match="injected failure"):
        run(config, meta_sync=True)
    assert destination.read_text() == "old"
    assert sorted(p.name for p in staging.iterdir()) == ["a.xmp"]


@pytest.mark.parametrize("error", [errno.EXDEV, errno.ENOTSUP, errno.ENOSPC])
def test_clone_errors_never_fallback(roots, monkeypatch, error):
    config, staging, target = roots
    source = image(staging / "a.jpg")
    destination = target / "a.jpg"
    os.link(source, destination)
    def fail(*args):
        raise OSError(error, "clone failure")
    monkeypatch.setattr(module, "_clonefile", fail)
    with pytest.raises(click.ClickException, match="clone failure"):
        run(config)
    assert destination.samefile(source)
    assert stat.S_IMODE(source.stat().st_mode) == 0o444
    assert list(target.iterdir()) == [destination]


def test_dry_run_and_retention(roots, tmp_path):
    config, staging, target = roots
    image(staging / "a.jpg")
    (target / "orphan.jpg").write_text("keep image")
    (staging / "orphan.xmp").write_text("keep metadata")
    (target / "a.xmp").write_text("new")
    before = snapshot(tmp_path)
    run(config, dry=True)
    assert snapshot(tmp_path) == before
    run(config)
    assert (target / "orphan.jpg").read_text() == "keep image"
    assert (staging / "orphan.xmp").read_text() == "keep metadata"


def test_platform_rejected(roots, monkeypatch):
    monkeypatch.setattr(module.sys, "platform", "linux")
    with pytest.raises(click.ClickException, match="macOS"):
        run(roots[0])


def test_cli_validation_nonzero(roots, monkeypatch):
    config, staging, target = roots
    monkeypatch.setattr("dam.cli.prepare_config", lambda: None)
    monkeypatch.setattr("dam.cli.load_config", lambda: config)
    (staging / "writable.jpg").write_text("unsafe")
    result = CliRunner().invoke(cli, ["sync", "--no-dry"])
    assert result.exit_code != 0
    assert "read-only" in result.output


def test_independent_readonly_target_keeps_edits(roots):
    config, staging, target = roots
    source = image(staging / "a.jpg")
    destination = target / "a.jpg"
    destination.write_text("target edit")
    destination.chmod(0o400)
    inode = destination.stat().st_ino
    run(config, file_sync=True)
    assert destination.stat().st_ino == inode
    assert destination.read_text() == "target edit"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert stat.S_IMODE(source.stat().st_mode) == 0o444


def test_clone_publication_failure_keeps_shared_target(roots, monkeypatch):
    config, staging, target = roots
    source = image(staging / "a.jpg")
    destination = target / "a.jpg"
    os.link(source, destination)
    def fail(*args):
        raise OSError(errno.EIO, "replacement failed")
    monkeypatch.setattr(module.os, "replace", fail)
    with pytest.raises(click.ClickException, match="replacement failed"):
        run(config)
    assert destination.samefile(source)
    assert destination.read_bytes() == b"original image"
    assert stat.S_IMODE(source.stat().st_mode) == 0o444
    assert list(target.iterdir()) == [destination]


def test_clonefile_reports_errno_and_paths(tmp_path, monkeypatch):
    class FakeClone:
        def __call__(self, source, destination, flags):
            assert flags == 0
            assert isinstance(source, bytes) and isinstance(destination, bytes)
            module.ctypes.set_errno(errno.EXDEV)
            return -1
    class FakeLibrary:
        clonefile = FakeClone()
    monkeypatch.setattr(module.ctypes, "CDLL", lambda *args, **kwargs: FakeLibrary())
    with pytest.raises(OSError) as caught:
        module._clonefile(tmp_path / "source", tmp_path / "target")
    assert caught.value.errno == errno.EXDEV
    assert str(tmp_path / "source") in str(caught.value)
    assert str(tmp_path / "target") in str(caught.value)
    assert "no fallback" in str(caught.value)
