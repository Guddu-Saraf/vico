import typer

from vico.commands.create import create
from vico.commands.init import init
from vico.commands.close import close
from vico.commands.cwd import cwd


app = typer.Typer()

app.command()(create)
app.command()(init)
app.command()(close)
app.command()(cwd)


if __name__ == "__main__":
    app()