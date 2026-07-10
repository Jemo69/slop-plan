import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.status import Status
from plan_cli.config import set_api_key, set_api_url, get_api_url, clear_api_key, get_email, set_email
from plan_cli.api import PlanAPI, PlanAPIError, PlanConnectionError

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
    password: str = typer.Option(None, "--password", "-p", help="Your password (min 6 chars)"),
    api_url: str = typer.Option(None, "--api-url", help="API server URL"),
):
    """Initialize plan CLI with your account."""
    if not email:
        email = typer.prompt("Your email")
    if not password:
        password = typer.prompt("Password", hide_input=True, min_length=6)
    _ensure_api_url(api_url)

    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.register(email, password))
        set_api_key(result["api_key"])
        set_email(email)
        console.print("[green]Successfully registered![/green]")
        console.print(f"Email: {result['email']}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        if "already registered" in str(e.detail).lower():
            console.print("[yellow]Email already registered. Logging in...[/yellow]")
            try:
                with console.status("[dim]Working...[/dim]"):
                    result = asyncio.run(api.login(email, password))
                set_api_key(result["api_key"])
                console.print("[green]Successfully logged in![/green]")
            except PlanConnectionError:
                console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
                raise typer.Exit(1)
            except PlanAPIError as e2:
                console.print(f"[red]Error: {e2.detail}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error: {e.detail}[/red]")
            raise typer.Exit(1)


@app.command()
def login(
    email: str = typer.Option(None, "--email", "-e", help="Your email address"),
    password: str = typer.Option(None, "--password", "-p", help="Your password"),
    api_url: str = typer.Option(None, "--api-url", help="API server URL"),
):
    """Login to an existing account."""
    if not email:
        email = typer.prompt("Your email")
    if not password:
        password = typer.prompt("Password", hide_input=True)
    _ensure_api_url(api_url)

    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.login(email, password))
        set_api_key(result["api_key"])
        set_email(email)
        console.print("[green]Successfully logged in![/green]")
        console.print(f"Email: {result['email']}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def logout():
    """Logout and remove stored credentials."""
    clear_api_key()
    console.print("[green]Logged out.[/green]")


@app.command()
def whoami():
    """Show current logged in user."""
    from plan_cli.config import get_api_key
    key = get_api_key()
    email = get_email()
    if not key:
        console.print("[yellow]Not logged in.[/yellow]")
        raise typer.Exit(1)
    console.print(f"Email:    {email or 'unknown'}")
    console.print(f"API Key:  {key[:8]}...{key[-4:]}" if len(key) > 12 else f"API Key:  {key}")
