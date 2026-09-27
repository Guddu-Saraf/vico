import os
import subprocess
from pathlib import Path

import typer
from alembic.config import Config
from alembic.script import ScriptDirectory


def get_venv_python(project_path: Path) -> Path:
    """
    Resolve the project's own virtual environment interpreter.

    Alembic, and the target project's own SQLAlchemy models (imported by
    env.py), need to run inside the project's `.venv` -- not whatever
    environment the `vico` CLI itself happens to be installed in. Those
    are two different Python environments, and the project's runtime
    dependencies live in the former, not necessarily the latter.
    """
    venv_path = project_path / ".venv"

    if os.name == "nt":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"

    if not python_path.exists():
        raise RuntimeError(
            "No virtual environment found for this project. "
            "Run 'vico init' first."
        )

    return python_path


def _get_alembic_paths(project_path: Path) -> tuple[Path, Path]:
    migration_path = project_path / "vico" / "migration"
    ini_path = migration_path / "alembic.ini"

    if not ini_path.exists():
        raise RuntimeError(
            "Database migration is not initialized. "
            "Run 'vico db' first."
        )

    return migration_path, ini_path


def _get_alembic_config(project_path: Path) -> Config:
    migration_path, ini_path = _get_alembic_paths(project_path)

    config = Config(str(ini_path))
    config.set_main_option(
        "script_location",
        str(migration_path),
    )

    return config


def _run_alembic(project_path: Path, ini_path: Path, *args: str) -> None:
    subprocess.run(
        [
            str(get_venv_python(project_path)),
            "-m",
            "alembic",
            "-c",
            str(ini_path),
            *args,
        ],
        cwd=project_path,
        check=True,
    )


def syn(project_path: Path, migration_name: str) -> None:
    _, ini_path = _get_alembic_paths(project_path)
    config = _get_alembic_config(project_path)
    script = ScriptDirectory.from_config(config)

    # Refuse to create a migration whose message collides with an
    # existing one -- alembic never enforces uniqueness on this text,
    # and letting duplicates accumulate is exactly what makes `res()`
    # ambiguous later.
    duplicate = next(
        (rev for rev in script.walk_revisions() if rev.doc == migration_name),
        None,
    )
    if duplicate is not None:
        raise RuntimeError(
            f"A migration named '{migration_name}' already exists "
            f"(revision {duplicate.revision}). Choose a different name."
        )

    _run_alembic(project_path, ini_path, "revision", "--autogenerate", "-m", migration_name)
    _run_alembic(project_path, ini_path, "upgrade", "head")


def run_syn(project_path: Path, migration_name: str) -> None:
    """CLI wrapper for database synchronization."""

    try:
        syn(project_path, migration_name)
    except subprocess.CalledProcessError as exc:
        typer.echo(f"Migration failed (exit code {exc.returncode}).", err=True)
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"Migration '{migration_name}' created "
        "and database upgraded to head."
    )


def list_history(project_path: Path) -> None:
    _, ini_path = _get_alembic_paths(project_path)
    _run_alembic(project_path, ini_path, "history")


def run_list_history(project_path: Path) -> None:
    try:
        list_history(project_path)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Migration history failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)


def res(project_path: Path, migration_name: str) -> None:
    _, ini_path = _get_alembic_paths(project_path)
    config = _get_alembic_config(project_path)
    script = ScriptDirectory.from_config(config)

    # Prefer an exact revision-ID match (unique, including abbreviated
    # hash prefixes) before falling back to matching by the human-readable
    # message. Alembic never guarantees message uniqueness, so silently
    # taking "whichever matches first" -- especially across a graph with
    # multiple branches/heads -- risks downgrading the wrong lineage
    # entirely, not just picking the wrong revision.
    try:
        target = script.get_revision(migration_name)
    except Exception:
        target = None

    if target is None:
        matches = [
            rev for rev in script.walk_revisions()
            if rev.doc == migration_name
        ]
        if not matches:
            raise RuntimeError(f"Migration '{migration_name}' not found.")
        if len(matches) > 1:
            ids = ", ".join(rev.revision for rev in matches)
            raise RuntimeError(
                f"Multiple migrations are named '{migration_name}' "
                f"({ids}). Re-run with one of these revision IDs instead "
                "of the name to disambiguate."
            )
        target = matches[0]

    downgrade_target = target.down_revision or "base"

    if isinstance(downgrade_target, tuple):
        # A merge revision has multiple parents -- there's no single
        # correct "the" branch to downgrade to, so refuse to guess.
        raise RuntimeError(
            f"Migration '{target.revision}' is a merge point with multiple "
            f"parent revisions {downgrade_target}. Downgrade to one of "
            "those revision IDs explicitly instead of by name."
        )

    _run_alembic(project_path, ini_path, "downgrade", downgrade_target)


def run_res(project_path: Path, migration_name: str) -> None:
    try:
        res(project_path, migration_name)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Migration reverse failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"Database downgraded to '{migration_name}'."
    )


def up(project_path: Path) -> None:
    _, ini_path = _get_alembic_paths(project_path)
    _run_alembic(project_path, ini_path, "upgrade", "head")


def run_up(project_path: Path) -> None:
    try:
        up(project_path)
    except subprocess.CalledProcessError as exc:
        typer.echo(
            f"Database upgrade failed (exit code {exc.returncode}).",
            err=True,
        )
        raise typer.Exit(code=1)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    typer.echo("Database upgraded to head.")
