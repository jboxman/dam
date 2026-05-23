from pathlib import Path

import pytest
from click.testing import CliRunner

from dam.cli import cli
from dam.commands.apply_copyright import apply_copyright
from dam.commands.apply_rotation import apply_rotation
from dam.commands.cleanup import cleanup
from dam.commands.compare import compare
from dam.commands.ingest import ingest
from dam.commands.sync import sync
from dam.commands.what_can import what_can
from dam.config import load_config, prepare_config
from dam.external import CommandResult


def test_what_can_reports_missing_actions(monkeypatch, tmp_path, capsys):
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    (photo_dir / ".copyright").touch()

    what_can(photo_dir)

    out = capsys.readouterr().out
    assert "ROTATE" in out
    assert "COPYRIGHT" not in out


def test_apply_copyright_marks_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    prepare_config()
    dam_dir = tmp_path / ".dam"
    args_file = dam_dir / "tester-copyright.conf"
    args_file.write_text("-Artist=Tester\n")
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    config = load_config()

    def fake_run_exiftool(**kwargs):
        return CommandResult(["exiftool"], "  2 image files updated\n", "", 0)

    monkeypatch.setattr("dam.commands.apply_copyright.run_exiftool", fake_run_exiftool)

    apply_copyright(config, photo_dir, dry=False)

    assert (photo_dir / ".copyright").exists()


def test_apply_rotation_dry_logs_commands(tmp_path, monkeypatch, capsys):
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    (photo_dir / "a.jpg").write_text("x")

    calls = []

    def fake_run_exiftran(path, **kwargs):
        calls.append((path, kwargs))
        return CommandResult(["exiftran"], "", "", 0)

    monkeypatch.setattr("dam.commands.apply_rotation.run_exiftran", fake_run_exiftran)

    apply_rotation(photo_dir, dry=True)

    assert calls[0][1]["execute"] is False


def test_ingest_uses_testname_in_dry_run(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    prepare_config()
    photo_dir = tmp_path / "incoming"
    photo_dir.mkdir()
    (photo_dir / ".copyright").touch()
    config = load_config()

    captured = {}

    def fake_run_exiftool(**kwargs):
        captured.update(kwargs)
        return CommandResult(["exiftool"], "a --> b\n", "", 0)

    monkeypatch.setattr("dam.commands.ingest.run_exiftool", fake_run_exiftool)

    ingest(config, photo_dir, dry=True)

    assert any("TestName<" in value for value in captured["extra_args"])


def test_ingest_uses_apple_pattern_when_export_db_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    prepare_config()
    photo_dir = tmp_path / "incoming"
    photo_dir.mkdir()
    (photo_dir / ".copyright").touch()
    (photo_dir / ".osxphotos_export.db").touch()
    config = load_config()

    captured = {}

    def fake_run_exiftool(**kwargs):
        captured.update(kwargs)
        return CommandResult(["exiftool"], "", "", 0)

    monkeypatch.setattr("dam.commands.ingest.run_exiftool", fake_run_exiftool)

    ingest(config, photo_dir, dry=True)

    assert any("${filename;s/\\.[^.]*$//}" in value for value in captured["extra_args"])


def test_cleanup_removes_backup_files(tmp_path):
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    (photo_dir / ".ingest").touch()
    backup = photo_dir / "a.jpg_original"
    tilde = photo_dir / "b.jpg~"
    backup.write_text("x")
    tilde.write_text("x")

    cleanup(photo_dir, dry=False)

    assert not backup.exists()
    assert not tilde.exists()
    assert (photo_dir / ".clean").exists()


def test_sync_creates_link_copies_xmp_and_prunes_orphans(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    config = load_config()
    staging = config.staging_user_dir / "2020/01/01"
    digikam = config.digikam_user_dir / "2020/01/01"
    staging.mkdir(parents=True)
    digikam.mkdir(parents=True)

    source_image = staging / "a.jpg"
    source_image.write_text("jpg-data")
    source_xmp = digikam / "a.jpg.xmp"
    source_xmp.write_text("xmp-data")
    orphan_image = digikam / "orphan.jpg"
    orphan_image.write_text("old")
    orphan_xmp = staging / "orphan.jpg.xmp"
    orphan_xmp.write_text("old-xmp")

    sync(config, dry=False, file_sync=False, meta_sync=False)

    linked_image = digikam / "a.jpg"
    assert linked_image.exists()
    assert source_image.stat().st_ino == linked_image.stat().st_ino
    assert (staging / "a.jpg.xmp").read_text() == "xmp-data"
    assert not orphan_image.exists()
    assert not orphan_xmp.exists()


def test_compare_reports_missing_files(monkeypatch, tmp_path, capsys):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    results = [
        CommandResult(["exiftool"], "/src^one.jpg^stamp1\n/src^two.jpg^stamp2\n", "", 0),
        CommandResult(["exiftool"], "/dst^one.jpg^stamp1\n", "", 0),
    ]

    def fake_run_exiftool(**kwargs):
        return results.pop(0)

    monkeypatch.setattr("dam.commands.compare.run_exiftool", fake_run_exiftool)

    compare(source_dir, target_dir)

    out = capsys.readouterr().out
    assert "Missing /src/two.jpg" in out


def test_rm_rejected_is_exposed_and_unimplemented(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    runner = CliRunner()

    result = runner.invoke(cli, ["rm-rejected"])

    assert result.exit_code != 0
    assert "not implemented" in result.output
