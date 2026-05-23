from click.testing import CliRunner

from dam.cli import cli


def test_help_lists_commands(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "what-can" in result.output
    assert "apply-copyright" in result.output
    assert "rm-rejected" in result.output


def test_sync_defaults_to_both_modes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", "tester")

    called = {}

    def fake_sync(config, *, dry, file_sync, meta_sync):
        called["dry"] = dry
        called["file_sync"] = file_sync
        called["meta_sync"] = meta_sync

    monkeypatch.setattr("dam.cli.sync", fake_sync)
    runner = CliRunner()

    result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    assert called == {"dry": True, "file_sync": False, "meta_sync": False}
