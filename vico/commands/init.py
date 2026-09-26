import shutil
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
        save_current_project(project_path)
    except Exception as exc:
        typer.echo(f"Failed to register project: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Project registered: {project_path}")