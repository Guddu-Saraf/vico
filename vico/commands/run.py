import shutil
import subprocess
import sys

import typer

from vico.core.project import get_current_project


def run(dev: bool = typer.Option(False, "--dev")):
    """Run the FastAPI application."""

    project_path = get_current_project()
    if project_path is None or not project_path.exists():
        typer.echo("No active Vico project. Run 'vico init' first.", err=True)
        raise typer.Exit(code=1)

    # Check uv
    if shutil.which("uv") is None:
        typer.echo("uv is not installed.")
        typer.echo("Installing uv...")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "uv"],
                check=True,
            )
        except subprocess.CalledProcessError:
            typer.echo("Failed to install uv.", err=True)
            raise typer.Exit(code=1)

        if shutil.which("uv") is None:
            typer.echo(
                "uv was installed but isn't on your PATH. "
                "Open a new shell (or add its install location to PATH) and try again.",
                err=True,
            )
            raise typer.Exit(code=1)

        typer.echo("uv installed successfully.")

    command = ["uv", "run", "uvicorn", "main:app"]

    if dev:
        command.append("--reload")

    try:
        subprocess.run(command, check=True, cwd=project_path)
    except subprocess.CalledProcessError as exc:
        raise typer.Exit(code=exc.returncode)
    except FileNotFoundError:
        typer.echo("Could not find 'uv' to run the command.", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        raise typer.Exit(code=130)