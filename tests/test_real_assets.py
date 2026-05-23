import shutil

import pytest

from dam.commands.compare import compare
from dam.commands.ingest import ingest
from dam.config import load_config, prepare_config
from dam.external import run_exiftool

from conftest import copy_asset


EXIFTOOL = shutil.which("exiftool")


@pytest.mark.skipif(EXIFTOOL is None, reason="exiftool is not installed")
def test_run_exiftool_reads_real_jpg_metadata(tmp_path):
    jpg = copy_asset("20160602-112716-1000140.jpg", tmp_path / "photo.jpg")

    result = run_exiftool(
        path=jpg,
        extra_args=["-s3", "-Model", "-DateTimeOriginal"],
        dry=False,
    )

    assert result.stdout_lines[0] == "NIKON D3100"
    assert result.stdout_lines[1] == "2016:06:02 11:27:16"


@pytest.mark.skipif(EXIFTOOL is None, reason="exiftool is not installed")
def test_run_exiftool_reads_real_nef_metadata(tmp_path):
    nef = copy_asset("20160602-112716-1000140.nef", tmp_path / "photo.nef")

    result = run_exiftool(
        path=nef,
        extra_args=["-s3", "-Model"],
        dry=False,
    )

    assert result.stdout_lines == ["NIKON D3100"]


@pytest.mark.skipif(EXIFTOOL is None, reason="exiftool is not installed")
def test_ingest_dry_run_with_real_assets_reports_matches(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    prepare_config()
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / ".copyright").touch()
    copy_asset("20160602-112716-1000140.jpg", incoming / "20160602-112716-1000140.jpg")
    copy_asset("20160602-112716-1000140.nef", incoming / "20160602-112716-1000140.nef")
    config = load_config()

    ingest(config, incoming, dry=True)

    out = capsys.readouterr().out
    assert "Files matched: 2" in out
    assert "20160602-112716-1000140.jpg" in out
    assert "20160602-112716-1000140.nef" in out
    assert "/2016/06/02/20160602-112716" in out


@pytest.mark.skipif(EXIFTOOL is None, reason="exiftool is not installed")
def test_compare_with_real_assets_reports_missing(monkeypatch, tmp_path, capsys):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    copy_asset("20160602-112716-1000140.jpg", source / "20160602-112716-1000140.jpg")
    copy_asset("20180513-153526.jpg", source / "20180513-153526.jpg")
    copy_asset("20160602-112716-1000140.jpg", target / "20160602-112716-1000140.jpg")

    compare(source, target)

    out = capsys.readouterr().out
    assert "Missing" in out
    assert "20180513-153526.jpg" in out
