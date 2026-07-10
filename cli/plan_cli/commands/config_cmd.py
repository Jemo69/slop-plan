import typer
from rich.console import Console
from plan_cli.config import load_config, get_api_url, set_api_url

console = Console()
app = typer.Typer(help="Configuration commands")


@app.command("show")
def show():
    config = load_config()
    api_url = config.get('api_url', 'http://localhost:8000')
    has_key = bool(config.get('api_key'))
    console.print(f"API URL: {api_url}")
    console.print(f"API Key: {'set' if has_key else 'not set'}")
    console.print(f"Config file: {config}")


@app.command("set")
def set_cmd(
    api_url: str = typer.Option(None, "--api-url", help="API server URL"),
):
    if not api_url:
        console.print("[red]--api-url is required[/red]")
        raise typer.Exit(1)
    set_api_url(api_url)
    console.print(f"[green]API URL set to: {api_url}[/green]")


@app.command("get")
def get():
    console.print(get_api_url())
