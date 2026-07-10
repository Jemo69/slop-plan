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
    key_display = f"{config['api_key'][:8]}...{config['api_key'][-4:]}" if has_key else "not set"
    console.print(f"API URL:  {api_url}")
    console.print(f"API Key:  {key_display}")
    console.print(f"Config:   ~/.plan-cli/config.json")


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
