import os
from pathlib import Path

import typer

from vico.core.project import get_current_project, get_project_file


def close():
    """Close the current Vico project."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.")
        raise typer.Exit(code=1)

    # Check that the registered project still exists
    if not project_path.exists():
        typer.echo("Current project no longer exists.")
    else:
        typer.echo(f"Closing Vico project: {project_path}")

    # Remove current project state
    project_file = get_project_file()

    if project_file.exists():
        project_file.unlink()

    typer.echo("Vico project closed.")

    # If the shell that invoked this CLI currently has this project's venv
    # active, VIRTUAL_ENV was inherited into this process's environment.
    # This is a real check, not a guess: `deactivate` itself is the same
    # command on cmd.exe, PowerShell, bash, zsh, fish and csh, so there's
    # no OS/shell branching needed the way there is for activation.
    venv_path = project_path / ".venv"
    active_venv = os.environ.get("VIRTUAL_ENV")

    if active_venv and Path(active_venv).resolve() == venv_path.resolve():
        typer.echo("Run 'deactivate' to exit the virtual environment.")
