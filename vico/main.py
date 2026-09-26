import typer

from vico.commands.create import create
from vico.commands.init import init
from vico.commands.close import close


app = typer.Typer()

app.command()(create)
app.command()(init)
app.command()(close)


if __name__ == "__main__":
    app()