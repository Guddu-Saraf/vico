import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

from vico.commands.db_migration import run_syn
from vico.core.project import get_current_project
# from vico.commands.db_migration import run_list_history, run_syn
from vico.commands.db_migration import (
    run_list_history,
    run_res,
    run_syn,
    run_up,
)
app = typer.Typer()


def setup_alembic(project_path: Path) -> None:
    migration_path = project_path / "vico" / "migration"

    if migration_path.exists() and any(migration_path.iterdir()):
        raise RuntimeError(
            "Vico migration setup already exists."
        )

    migration_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "init",
                "alembic",
            ],
            cwd=temp_path,
            check=True,
        )

        generated = temp_path / "alembic"
        generated_ini = temp_path / "alembic.ini"

        shutil.move(str(generated), str(migration_path))
        shutil.move(
            str(generated_ini),
            str(migration_path / "alembic.ini"),
        )

    _configure_alembic_ini(migration_path)
    _write_vico_env(migration_path)


def _configure_alembic_ini(migration_path: Path) -> None:
    ini_path = migration_path / "alembic.ini"
    content = ini_path.read_text(encoding="utf-8")

    lines = content.splitlines()

    for index, line in enumerate(lines):
        if line.strip().startswith("script_location"):
            lines[index] = "script_location = %(here)s"

    content = "\n".join(lines) + "\n"

    content = content.replace(
        "sqlalchemy.url = driver://user:pass@localhost/dbname",
        "sqlalchemy.url =",
    )

    ini_path.write_text(content, encoding="utf-8")


def _write_vico_env(migration_path: Path) -> None:
    env_path = migration_path / "env.py"

    env_path.write_text(
        """import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from vico.config import get_database_url
from vico.database import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option(
    "sqlalchemy.url",
    get_database_url(),
)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""",
        encoding="utf-8",
    )


@app.callback(invoke_without_command=True)
def db(ctx: typer.Context):
    """Vico database management."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.", err=True)
        raise typer.Exit(code=1)

    if ctx.invoked_subcommand is None:
        try:
            setup_alembic(project_path)
        except subprocess.CalledProcessError:
            typer.echo("Alembic setup failed.", err=True)
            raise typer.Exit(code=1)
        except Exception as exc:
            typer.echo(f"Database setup failed: {exc}", err=True)
            raise typer.Exit(code=1)

        typer.echo("Vico database migration system initialized.")


@app.command()
def syn(name: str):
    """Create a migration and upgrade the database to head."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.", err=True)
        raise typer.Exit(code=1)

    run_syn(project_path, name)

@app.command("list")
def list_history():
    """Show migration history."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.", err=True)
        raise typer.Exit(code=1)

    run_list_history(project_path)

@app.command("res")
def reverse(migration_name: str):
    """Reverse the database to a migration."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.", err=True)
        raise typer.Exit(code=1)

    run_res(project_path, migration_name)


@app.command("up")
def upgrade():
    """Apply all migrations to head."""

    project_path = get_current_project()

    if project_path is None:
        typer.echo("No active Vico project.", err=True)
        raise typer.Exit(code=1)

    run_up(project_path)
