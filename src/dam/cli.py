from __future__ import annotations

from pathlib import Path

import click

from dam.commands.apply_copyright import apply_copyright
from dam.commands.apply_rotation import apply_rotation
from dam.commands.cleanup import cleanup
from dam.commands.compare import compare
from dam.commands.ingest import ingest
from dam.commands.rm_rejected import rm_rejected
from dam.commands.sync import sync
from dam.commands.what_can import what_can
from dam.config import load_config, prepare_config


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    prepare_config()
    ctx.obj = load_config()


@cli.command("what-can")
@click.argument("photo_dir", type=click.Path(path_type=Path))
def what_can_cmd(photo_dir: Path) -> None:
    what_can(photo_dir)


@cli.command("ingest")
@click.argument("photo_dir", type=click.Path(path_type=Path))
@click.option("--dry/--no-dry", default=True, show_default=True)
@click.pass_obj
def ingest_cmd(config, photo_dir: Path, dry: bool) -> None:
    ingest(config, photo_dir, dry=dry)


@cli.command("apply-copyright")
@click.argument("photo_dir", type=click.Path(path_type=Path))
@click.option("--dry/--no-dry", default=True, show_default=True)
@click.pass_obj
def apply_copyright_cmd(config, photo_dir: Path, dry: bool) -> None:
    apply_copyright(config, photo_dir, dry=dry)


@cli.command("apply-rotation")
@click.argument("photo_dir", type=click.Path(path_type=Path))
@click.option("--dry/--no-dry", default=True, show_default=True)
def apply_rotation_cmd(photo_dir: Path, dry: bool) -> None:
    apply_rotation(photo_dir, dry=dry)


@cli.command("sync")
@click.option("--dry/--no-dry", default=True, show_default=True)
@click.option("--file-sync", is_flag=True, default=False)
@click.option("--meta-sync", is_flag=True, default=False)
@click.pass_obj
def sync_cmd(config, dry: bool, file_sync: bool, meta_sync: bool) -> None:
    sync(config, dry=dry, file_sync=file_sync, meta_sync=meta_sync)


@cli.command("cleanup")
@click.argument("photo_dir", type=click.Path(path_type=Path))
@click.option("--dry/--no-dry", default=True, show_default=True)
def cleanup_cmd(photo_dir: Path, dry: bool) -> None:
    cleanup(photo_dir, dry=dry)


@cli.command("compare")
@click.argument("source_dir", type=click.Path(path_type=Path))
@click.argument("target_dir", type=click.Path(path_type=Path))
def compare_cmd(source_dir: Path, target_dir: Path) -> None:
    compare(source_dir, target_dir)


@cli.command("rm-rejected")
@click.option("--dry/--no-dry", default=True, show_default=True)
@click.option("--path", "target_path", type=click.Path(path_type=Path), default=None)
def rm_rejected_cmd(dry: bool, target_path: Path | None) -> None:
    rm_rejected(dry=dry, target_path=target_path)


def main() -> None:
    cli()
