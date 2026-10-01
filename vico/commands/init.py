import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import venv
from itertools import cycle
from pathlib import Path

import typer

from vico.core.project import save_current_project


def _spin(stop_event: threading.Event, message: str, start_time: float) -> None:
    """Render an indeterminate spinner + elapsed time while a background task runs."""
    for frame in cycle("|/-\\"):
        if stop_event.is_set():
            break
        elapsed = time.monotonic() - start_time
        sys.stdout.write(f"\r{message} {frame} ({elapsed:0.1f}s)")
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the line so the final "created" message isn't mixed with spinner chars
    sys.stdout.write("\r" + " " * (len(message) + 12) + "\r")
    sys.stdout.flush()


def _create_venv_with_spinner(venv_path: Path) -> None:
    """Run venv.create() on a worker thread while a spinner renders on the main thread."""
    stop_event = threading.Event()
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            venv.create(venv_path, with_pip=True)
        except BaseException as exc:  # noqa: BLE001 - re-raised on main thread below
            error.append(exc)
        finally:
            stop_event.set()

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    _spin(stop_event, "Creating virtual environment...", time.monotonic())
    worker.join()

    if error:
        raise error[0]


# Vico is currently only published on TestPyPI, pinned to this version.
# Once it's released on PyPI proper, drop the index args and (if desired)
# the version pin below.
_TEST_PYPI_INDEX_URL = "https://test.pypi.org/simple/"
_TEST_PYPI_VICO_VERSION = "0.1.4"


# def _install_vico(venv_path: Path) -> None:
#     """Install Vico into the project's virtual environment."""

#     if platform.system() == "Windows":
#         python_executable = venv_path / "Scripts" / "python.exe"
#     else:
#         python_executable = venv_path / "bin" / "python"

#     subprocess.run(
#         [
#             str(python_executable),
#             "-m",
#             "pip",
#             "install",
#             "--index-url",
#             _TEST_PYPI_INDEX_URL,
#             # TestPyPI doesn't mirror Vico's dependencies, so fall back to
#             # regular PyPI for anything it can't find (fastapi, uvicorn, etc.).
#             "--extra-index-url",
#             "https://pypi.org/simple",
#             f"vico=={_TEST_PYPI_VICO_VERSION}",
#         ],
#         check=True,
#     )
def _install_vico(venv_path: Path) -> None:
    """Install Vico into the project's virtual environment."""

    if platform.system() == "Windows":
        python_executable = venv_path / "Scripts" / "python.exe"
    else:
        python_executable = venv_path / "bin" / "python"

    subprocess.run(
        [str(python_executable), "-m", "pip", "install", "vico-cli"],
        check=True,
    )

def _activation_hint(venv_path: Path) -> str:
    """
    Best-effort activation command for whatever shell invoked this CLI.

    IMPORTANT: this process cannot activate the venv *for* the user.
    Activation works by sourcing a script into the CURRENT shell process,
    which changes that shell's own environment variables. A subprocess
    (this CLI) has no way to reach back into its parent shell's
    environment -- any activation "run" internally here would be invisible
    and discarded the moment this process exits. The best this can do is
    print the correct command for the user to run themselves.
    """
    system = platform.system()

    if system == "Windows":
        scripts_dir = venv_path / "Scripts"

        if os.environ.get("MSYSTEM"):
            # Git Bash / MSYS2 / MinGW shell - reliably detectable via MSYSTEM
            return f"source {scripts_dir / 'activate'}"

        # From inside a subprocess there is no reliable, dependency-free way
        # to tell cmd.exe apart from PowerShell (both leave similar env
        # vars), so show both rather than guess and risk giving the wrong one.
        cmd_activate = scripts_dir / "activate.bat"
        ps1_activate = scripts_dir / "Activate.ps1"
        return (
            f"cmd.exe:     {cmd_activate}\n"
            f"  PowerShell:  {ps1_activate}"
        )

    # POSIX: Linux, macOS
    bin_dir = venv_path / "bin"
    shell = os.environ.get("SHELL", "")

    if shell.endswith("fish"):
        return f"source {bin_dir / 'activate.fish'}"
    if shell.endswith(("csh", "tcsh")):
        return f"source {bin_dir / 'activate.csh'}"

    # Default: bash/zsh/sh and anything else POSIX-compatible
    return f"source {bin_dir / 'activate'}"


def init():
    """Initialize the current Vico project."""

    project_path = Path.cwd()
    venv_path = project_path / ".venv"

    if venv_path.exists():
        typer.echo("Virtual environment already exists.")
    else:
        try:
            _create_venv_with_spinner(venv_path)
        except Exception as exc:
            typer.echo(f"Failed to create virtual environment: {exc}", err=True)
            shutil.rmtree(venv_path, ignore_errors=True)
            raise typer.Exit(code=1)

        typer.echo("Virtual environment created.")

        try:
            _install_vico(venv_path)
        except subprocess.CalledProcessError:
            typer.echo("Failed to install Vico in the virtual environment.", err=True)
            raise typer.Exit(code=1)

        typer.echo("Vico installed in the virtual environment.")

    try:
        save_current_project(project_path)
    except Exception as exc:
        typer.echo(f"Failed to register project: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Project registered: {project_path}")
    typer.echo(f"To activate the virtual environment, run:\n  {_activation_hint(venv_path)}")