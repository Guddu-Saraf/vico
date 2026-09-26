import typer

from vico.commands.create import create


app = typer.Typer()


@app.callback()
def callback():
    """Vico project scaffolding CLI."""
    # Empty callback: keeps Typer's subcommand semantics (e.g. `create`)
    # even with only one command registered — without this, Typer
    # collapses to a single top-level command with no subcommand name.


app.command(name="create")(create)


if __name__ == "__main__":
    app()