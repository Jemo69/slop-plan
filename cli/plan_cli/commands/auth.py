import asyncio
import typer
from rich.console import Console
from plan_cli.config import set_api_key, set_api_url
from plan_cli.api import PlanAPI, PlanAPIError

console = Console()
app = typer.Typer(help="Authentication commands")


@app.command()
def init(
    email: str = typer.Option(..., prompt=True, help="Your email address"),
    api_url: str = typer.Option("https://html-planner-server.vercel.app", help="API server URL"),
):
    """Initialize plan CLI with your account."""
    set_api_url(api_url)
    
    api = PlanAPI()
    
    try:
        result = asyncio.run(api.register(email))
        set_api_key(result["api_key"])
        console.print(f"[green]Successfully registered![/green]")
        console.print(f"API Key: [bold]{result['api_key']}[/bold]")
        console.print(f"Email: {result['email']}")
    except PlanAPIError as e:
        if "already registered" in str(e.detail).lower():
            console.print("[yellow]Email already registered. Logging in...[/yellow]")
            try:
                result = asyncio.run(api.login(email))
                set_api_key(result["api_key"])
                console.print(f"[green]Successfully logged in![/green]")
                console.print(f"API Key: [bold]{result['api_key']}[/bold]")
            except PlanAPIError as e2:
                console.print(f"[red]Error: {e2.detail}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error: {e.detail}[/red]")
            raise typer.Exit(1)


@app.command()
def login(
    email: str = typer.Option(..., prompt=True, help="Your email address"),
    api_url: str = typer.Option("https://html-planner-server.vercel.app", help="API server URL"),
):
    """Login to an existing account."""
    set_api_url(api_url)
    
    api = PlanAPI()
    
    try:
        result = asyncio.run(api.login(email))
        set_api_key(result["api_key"])
        console.print(f"[green]Successfully logged in![/green]")
        console.print(f"API Key: [bold]{result['api_key']}[/bold]")
        console.print(f"Email: {result['email']}")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)
