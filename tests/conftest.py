from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ASSETS = ROOT / "tests" / "assets"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def write_config(home: Path, payload: str = "{}") -> None:
    dam_dir = home / ".dam"
    dam_dir.mkdir(parents=True, exist_ok=True)
    (dam_dir / "config.json").write_text(payload)


def write_copyright_args(home: Path, user: str = "tester") -> Path:
    dam_dir = home / ".dam"
    dam_dir.mkdir(parents=True, exist_ok=True)
    path = dam_dir / f"{user}-copyright.conf"
    path.write_text("-Artist=Tester\n")
    return path


def set_home(monkeypatch, tmp_path: Path, user: str = "tester") -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USER", user)


def make_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


def asset_path(name: str) -> Path:
    return ASSETS / name


def copy_asset(name: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(asset_path(name).read_bytes())
    return destination
