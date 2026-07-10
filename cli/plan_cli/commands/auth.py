import asyncio
from typing import Optional
import typer
from rich.console import Console
from plan_cli.config import set_api_key, set_api_url, get_api_url
from plan_cli.api import PlanAPI, PlanAPIError

console = Console()
app = typer.Typer(help="Authentication commands")


def _ensure_api_url(api_url: Optional[str]):
    if api_url:
        set_api_url(api_url)
    else:
        current = get_api_url()
        set_api_url(current)


@app.command()
def init(
    email: str = typer.Option(None, "--email", "-e", help="Your email address"),
    api_url: str = typer.Option(None, "--api-url", help="API server URL"),
):
    """Initialize plan CLI with your account."""
    if not email:
        email = typer.prompt("Your email")
    _ensure_api_url(api_url)

    api = PlanAPI()

    try:
        result = asyncio.run(api.register(email))
        set_api_key(result["api_key"])
        console.print("[green]Successfully registered![/green]")
        console.print(f"API Key: [bold]{result['api_key']}[/bold]")
        console.print(f"Email: {result['email']}")
    except PlanAPIError as e:
        if "already registered" in str(e.detail).lower():
            console.print("[yellow]Email already registered. Logging in...[/yellow]")
            try:
                result = asyncio.run(api.login(email))
                set_api_key(result["api_key"])
                console.print("[green]Successfully logged in![/green]")
                console.print(f"API Key: [bold]{result['api_key']}[/bold]")
            except PlanAPIError as e2:
                console.print(f"[red]Error: {e2.detail}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error: {e.detail}[/red]")
            raise typer.Exit(1)


@app.command()
def login(
    email: str = typer.Option(None, "--email", "-e", help="Your email address"),
    api_url: str = typer.Option(None, "--api-url", help="API server URL"),
):
    """Login to an existing account."""
    if not email:
        email = typer.prompt("Your email")
    _ensure_api_url(api_url)

    api = PlanAPI()

    try:
        result = asyncio.run(api.login(email))
        set_api_key(result["api_key"])
        console.print("[green]Successfully logged in![/green]")
        console.print(f"API Key: [bold]{result['api_key']}[/bold]")
        console.print(f"Email: {result['email']}")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)
