import json
import os
import secrets
from pathlib import Path


def get_vico_data_dir() -> Path:
    """Return Vico's user-level data directory."""

    if os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base_dir = Path(
            os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
        )

    vico_dir = base_dir / "vico"
    vico_dir.mkdir(parents=True, exist_ok=True)

    return vico_dir


def get_project_file() -> Path:
    """Return the file used to store the current project."""

    return get_vico_data_dir() / "project.json"


def save_current_project(project_path: Path) -> None:
    """Save the current Vico project path."""

    project_file = get_project_file()

    data = {
        "current_project": str(project_path.resolve())
    }

    # Write atomically: write to a temp file in the same directory, then
    # os.replace it over the target. This avoids leaving project.json
    # truncated/corrupt if the process is interrupted mid-write.
    #
    # The temp filename includes the PID and a random suffix so that two
    # concurrent `vico` processes (e.g. two terminals running `vico init`
    # around the same time) never share the same temp path -- without
    # this, one process's os.replace() can rename the other's temp file
    # out from under it, crashing the second with FileNotFoundError.
    tmp_file = project_file.with_name(
        f"{project_file.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    )

    try:
        tmp_file.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8",
        )
        os.replace(tmp_file, project_file)
    except BaseException:
        tmp_file.unlink(missing_ok=True)
        raise


def get_current_project() -> Path | None:
    """Return the current Vico project path."""

    project_file = get_project_file()

    if not project_file.exists():
        return None

    try:
        data = json.loads(
            project_file.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable registry file — treat as "no project
        # registered" rather than crashing every command that calls this.
        return None

    project_path = data.get("current_project")

    if not project_path:
        return None

    return Path(project_path)