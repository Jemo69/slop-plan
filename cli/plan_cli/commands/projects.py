import asyncio
import typer
from rich.console import Console
from rich.table import Table
from plan_cli.api import PlanAPI, PlanAPIError

console = Console()
app = typer.Typer(help="Project commands")


@app.command("list")
def list_projects():
    """List your projects."""
    api = PlanAPI()
    try:
        projects = asyncio.run(api.list_projects())
        if not projects:
            console.print("[yellow]No projects found. Create one with 'plan projects create'[/yellow]")
            return
        table = Table(title="Projects")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="dim")
        table.add_column("Created", style="dim")
        for p in projects:
            table.add_row(p["id"][:8] + "...", p["name"], p.get("description") or "", p["created_at"][:10] if p.get("created_at") else "")
        console.print(table)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("create")
def create_project(
    name: str = typer.Option(..., "--name", "-n", help="Project name"),
    description: str = typer.Option(None, "--description", "-d", help="Project description"),
):
    """Create a new project."""
    api = PlanAPI()
    try:
        result = asyncio.run(api.create_project(name=name, description=description))
        console.print("[green]Project created![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"Name: {result['name']}")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_project(
    project_id: str = typer.Argument(help="Project ID"),
):
    """Get project details."""
    api = PlanAPI()
    try:
        p = asyncio.run(api.get_project(project_id))
        console.print(f"[bold]Name:[/bold] {p['name']}")
        console.print(f"[bold]ID:[/bold] {p['id']}")
        console.print(f"[bold]Description:[/bold] {p.get('description') or ''}")
        console.print(f"[bold]Created:[/bold] {p.get('created_at')}")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_project(
    project_id: str = typer.Argument(help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a project."""
    if not force:
        if not typer.confirm(f"Delete project {project_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    api = PlanAPI()
    try:
        asyncio.run(api.delete_project(project_id))
        console.print("[green]Project deleted[/green]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)
