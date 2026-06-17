import typer
from rich.console import Console
from plan_cli.config import load_config, get_api_url, set_api_url

console = Console()
app = typer.Typer(help="Configuration commands")


@app.command()
def show():
    """Show current configuration."""
    config = load_config()
    console.print(f"API URL: {config.get('api_url', 'http://localhost:8000')}")
    console.print(f"API Key: {'set' if config.get('api_key') else 'not set'}")


@app.command()
def set(
    api_url: str = typer.Option(..., help="API server URL"),
):
    """Set the API URL."""
    set_api_url(api_url)
    console.print(f"[green]API URL set to: {api_url}[/green]")


@app.command()
def get():
    """Get the current API URL."""
    console.print(get_api_url())
