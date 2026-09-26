import shutil
from pathlib import Path

import typer

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates" / "default"


def create(
    name: str = typer.Argument(..., help="Name of the new project directory."),
):
    """Create a new project from the default template."""

    cleaned = name.strip()
    if not cleaned:
        typer.echo("Error: project name cannot be empty.", err=True)
        raise typer.Exit(code=1)

    if (
        Path(cleaned).is_absolute()
        or any(part in ("..", "") for part in Path(cleaned).parts)
        or "/" in cleaned
        or "\\" in cleaned
    ):
        typer.echo(f"Error: '{name}' is not a valid project name.", err=True)
        raise typer.Exit(code=1)

    project_dir = Path.cwd() / cleaned

    if project_dir.exists():
        typer.echo(f"Error: '{cleaned}' already exists.", err=True)
        raise typer.Exit(code=1)

    if not TEMPLATE_DIR.exists():
        typer.echo("Error: default template not found.", err=True)
        raise typer.Exit(code=1)

    try:
        shutil.copytree(TEMPLATE_DIR, project_dir)
    except FileExistsError:
        typer.echo(f"Error: '{cleaned}' already exists.", err=True)
        raise typer.Exit(code=1)
    except OSError as e:
        typer.echo(f"Error: failed to create project: {e}", err=True)
        shutil.rmtree(project_dir, ignore_errors=True)
        raise typer.Exit(code=1)

    typer.echo(f"Created project: {cleaned}")
    typer.echo(f"Location: {project_dir}")