import typer
from plan_cli.commands.auth import app as auth_app
from plan_cli.commands.plans import app as plans_app

app = typer.Typer(
    name="plan",
    help="HTML Plan Service CLI - Create, manage, and share HTML plans",
    no_args_is_help=True,
)

app.add_typer(auth_app, name="auth")
app.add_typer(plans_app, name="plans")


@app.command()
def version():
    """Show version information."""
    typer.echo("plan CLI v0.1.0")


if __name__ == "__main__":
    app()
