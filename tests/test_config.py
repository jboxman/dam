from dam.config import load_config, prepare_config


def test_load_config_uses_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")

    config = load_config()

    assert config.defaultUser == "tester"
    assert config.staging_user_dir.name == "tester"
    assert "tester" in config.photographers


def test_load_config_merges_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")
    dam_dir = tmp_path / ".dam"
    dam_dir.mkdir()
    (dam_dir / "config.json").write_text(
        '{"stagingDir": "/tmp/staging", "photographers": {"tester": {"copyrightArgs": "/tmp/custom.arg"}}}'
    )

    config = load_config()

    assert config.stagingDir == "/tmp/staging"
    assert str(config.copyright_args_for_user()) == "/tmp/custom.arg"


def test_prepare_config_creates_exiftool_conf(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    prepare_config()

    assert (tmp_path / ".dam" / "exiftool.conf").exists()
