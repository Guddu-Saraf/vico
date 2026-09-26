import shutil
import venv
from pathlib import Path

import typer

from vico.core.project import save_current_project


def init():
    """Initialize the current Vico project."""

    project_path = Path.cwd()
    venv_path = project_path / ".venv"

    # Create virtual environment
    if venv_path.exists():
        typer.echo("Virtual environment already exists.")
    else:
        typer.echo("Creating virtual environment...")

        try:
            venv.create(
                venv_path,
                with_pip=True,
            )
        except Exception as exc:
            typer.echo(f"Failed to create virtual environment: {exc}", err=True)
            # Don't leave a partial/broken .venv behind for the next run
            # to mistake for a valid, already-created environment.
            shutil.rmtree(venv_path, ignore_errors=True)
            raise typer.Exit(code=1)

        typer.echo("Virtual environment created.")

    # Register current project
    try:
        save_current_project(project_path)
    except Exception as exc:
        typer.echo(f"Failed to register project: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Project registered: {project_path}")