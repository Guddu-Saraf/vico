import typer

from vico.core.project import get_current_project


def cwd():
    """Show the current Vico project."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.")
        return

    if not project_path.exists():
        typer.echo(f"Current project: {project_path} (missing — this path no longer exists)")
        return

    typer.echo(f"Current project: {project_path}")