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