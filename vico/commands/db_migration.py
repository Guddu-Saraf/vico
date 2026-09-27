from pathlib import Path
import subprocess
import sys
import typer
from alembic import command
from alembic.config import Config
from alembic.config import Config
from alembic.script import ScriptDirectory

def _get_alembic_config(project_path: Path) -> Config:
    migration_path = project_path / "vico" / "migration"
    ini_path = migration_path / "alembic.ini"

    if not ini_path.exists():
        raise RuntimeError(
            "Database migration is not initialized. "
            "Run 'vico db' first."
        )

    config = Config(str(ini_path))

    config.set_main_option(
        "script_location",
        str(migration_path),
    )

    return config

def _get_alembic_paths(project_path: Path) -> tuple[Path, Path]:
    migration_path = project_path / "vico" / "migration"
    ini_path = migration_path / "alembic.ini"

    if not ini_path.exists():
        raise RuntimeError(
            "Database migration is not initialized. "
            "Run 'vico db' first."
        )

    return migration_path, ini_path

def syn(project_path: Path, migration_name: str) -> None:
    migration_path = project_path / "vico" / "migration"
    ini_path = migration_path / "alembic.ini"

    if not ini_path.exists():
        raise RuntimeError(
            "Database migration is not initialized. "
            "Run 'vico db' first."
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            "revision",
            "--autogenerate",
            "-m",
            migration_name,
        ],
        cwd=project_path,
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            "upgrade",
            "head",
        ],
        cwd=project_path,
        check=True,
    )

def run_syn(project_path: Path, migration_name: str) -> None:
    """CLI wrapper for database synchronization."""

    try:
        syn(project_path, migration_name)
    except Exception as exc:
        typer.echo(f"Migration failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"Migration '{migration_name}' created "
        "and database upgraded to head."
    )


def list_history(project_path: Path) -> None:
    _, ini_path = _get_alembic_paths(project_path)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            "history",
        ],
        cwd=project_path,
        check=True,
    )

def run_list_history(project_path: Path) -> None:
    try:
        list_history(project_path)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Migration history failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)

# def res(project_path: Path, migration_name: str) -> None:
#     _, ini_path = _get_alembic_paths(project_path)

#     subprocess.run(
#         [
#             sys.executable,
#             "-m",
#             "alembic",
#             "-c",
#             str(ini_path),
#             "downgrade",
#             migration_name,
#         ],
#         cwd=project_path,
#         check=True,
#     )

def res(project_path: Path, migration_name: str) -> None:
    migration_path, ini_path = _get_alembic_paths(project_path)

    config = Config(str(ini_path))

    config.set_main_option(
        "script_location",
        str(migration_path),
    )

    script = ScriptDirectory.from_config(config)

    target = None

    for revision in script.walk_revisions():
        if revision.doc == migration_name:
            target = revision
            break

    if target is None:
        raise RuntimeError(
            f"Migration '{migration_name}' not found."
        )

    downgrade_target = target.down_revision or "base"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            "downgrade",
            downgrade_target,
        ],
        cwd=project_path,
        check=True,
    )

def up(project_path: Path) -> None:
    _, ini_path = _get_alembic_paths(project_path)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            "upgrade",
            "head",
        ],
        cwd=project_path,
        check=True,
    )


def run_up(project_path: Path) -> None:
    try:
        up(project_path)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Database upgrade failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo("Database upgraded to head.")


def run_res(project_path: Path, migration_name: str) -> None:
    try:
        res(project_path, migration_name)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Migration reverse failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(
        f"Database downgraded to '{migration_name}'."
    )

