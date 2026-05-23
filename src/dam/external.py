from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import click


@dataclass
class CommandResult:
    args: List[str]
    stdout: str
    stderr: str
    returncode: int

    @property
    def stdout_lines(self) -> List[str]:
        return [line for line in self.stdout.splitlines() if line]

    @property
    def stderr_lines(self) -> List[str]:
        return [line for line in self.stderr.splitlines() if line]


def log_command(args: Sequence[str], dry: bool = False) -> None:
    prefix = "[DRY]" if dry else "[RUN]"
    click.echo(f"{prefix} {shlex.join(list(args))}")


def log_message(message: str, dry: bool = False) -> None:
    prefix = "[DRY]" if dry else "[RUN]"
    click.echo(f"{prefix} {message}")


def run_command(
    args: Sequence[str],
    *,
    dry: bool = False,
    execute: bool = True,
    check: bool = True,
    cwd: Path | None = None,
) -> CommandResult:
    log_command(args, dry=dry)
    if dry and not execute:
        return CommandResult(list(args), "", "", 0)

    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    result = CommandResult(
        args=list(args),
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )
    if check and result.returncode != 0:
        raise click.ClickException(format_failure(result))
    return result


def format_failure(result: CommandResult) -> str:
    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    details = stderr or stdout or f"command exited with status {result.returncode}"
    return f"Command failed: {shlex.join(result.args)}\n{details}"


def run_exiftool(
    *,
    path: Path,
    exiftool_config: Path | None = None,
    expr: Iterable[str] = (),
    file_types: Iterable[str] = (),
    extra_args: Iterable[str] = (),
    dry: bool = False,
    execute: bool = True,
    check: bool = True,
) -> CommandResult:
    args: List[str] = ["exiftool", "-m"]
    if exiftool_config is not None:
        args.extend(["-config", str(exiftool_config)])
    for arg in extra_args:
        args.append(str(arg))
    for expression in expr:
        args.extend(["-if", str(expression)])
    for file_type in file_types:
        args.extend(["-ext", str(file_type)])
    args.append(str(path))
    return run_command(args, dry=dry, execute=execute, check=check)


def run_exiftran(
    file_path: Path,
    *,
    dry: bool = False,
    execute: bool = True,
    check: bool = True,
) -> CommandResult:
    return run_command(
        ["exiftran", "-aipb", str(file_path)],
        dry=dry,
        execute=execute,
        check=check,
    )
