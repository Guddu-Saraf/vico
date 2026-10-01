import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from vico.core.project import get_current_project


REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "alembic": "alembic",
    "dotenv": "python-dotenv",
}


def is_project_venv_active(project_path: Path) -> bool:
    """Check whether the project's virtual environment is active.

    ``vico`` itself typically runs from its own installation (global
    install, pipx, etc.), so ``sys.executable`` reflects *that*
    interpreter, not whatever venv the user has activated in their
    shell. Comparing sys.executable to the project's venv python is
    therefore unreliable and fails even when the correct venv is
    active. Instead, check the VIRTUAL_ENV environment variable that
    activate.bat / Activate.ps1 set, and compare it to the project's
    .venv directory.
    """

    virtual_env = os.environ.get("VIRTUAL_ENV")

    if not virtual_env:
        return False

    active_venv = Path(virtual_env).resolve()
    project_venv = (project_path / ".venv").resolve()

    return active_venv == project_venv

def check_required_modules(project_path: Path) -> bool:
    """Check whether required modules are available in the project's venv.

    This must run *inside* the project's venv interpreter (via
    subprocess), not the currently running process: vico itself may be
    installed under a different Python entirely, so importlib.util
    .find_spec here would only ever inspect vico's own environment.
    """
    venv_python = project_path / ".venv" / "Scripts" / "python.exe"
    missing = []

    for module, package in REQUIRED_MODULES.items():
        result = subprocess.run(
            [str(venv_python), "-c", f"import {module}"],
            capture_output=True,
        )
        if result.returncode != 0:
            missing.append(package)

    if missing:
        typer.echo(
            "Required Vico modules are missing from the active virtual environment:",
            err=True,
        )

        for package in missing:
            typer.echo(f"  - {package}", err=True)

        typer.echo(
            "\nInstall Vico in this virtual environment with:",
            err=True,
        )
        typer.echo(
            "  python -m pip install vico",
            err=True,
        )

        return False

    return True


def run(dev: bool = typer.Option(False, "--dev")):
    """Run the FastAPI application."""

    project_path = get_current_project()

    if project_path is None or not project_path.exists():
        typer.echo(
            "No active Vico project. Run 'vico init' first.",
            err=True,
        )
        raise typer.Exit(code=1)

    # Make sure the project's virtual environment is active.
    if not is_project_venv_active(project_path):
        typer.echo(
            "Vico project virtual environment is not active.",
            err=True,
        )
        typer.echo(
            f"Activate it first:\n  {project_path / '.venv' / 'Scripts' / 'activate'}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Check Vico/application dependencies inside the active .venv.
    if not check_required_modules(project_path):
        raise typer.Exit(code=1)

    # Check uv.
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
        typer.echo(
            "Could not find 'uv' to run the command.",
            err=True,
        )
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        raise typer.Exit(code=130)