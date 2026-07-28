import asyncio
import json
import typer
from rich.console import Console
from rich.table import Table
from rich.status import Status
from plan_cli.api import PlanAPI, PlanAPIError, PlanConnectionError

console = Console()
app = typer.Typer(help="Project commands")


@app.command("list")
def list_projects(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    limit: int = typer.Option(None, "--limit", "-n", help="Max results to show"),
    offset: int = typer.Option(0, "--offset", help="Skip first N results"),
):
    """List your projects."""
    api = PlanAPI()
    try:
        with console.status("[dim]Working...[/dim]"):
            projects = asyncio.run(api.list_projects())
        if not projects:
            console.print("[yellow]No projects found. Create one with 'plan projects create'[/yellow]")
            return
        if as_json:
            console.print(json.dumps(projects, indent=2))
            return
        total = len(projects)
        projects = projects[offset:]
        if limit is not None:
            projects = projects[:limit]
        table = Table(title=f"Projects ({offset+1}-{min(offset+len(projects), total)} of {total})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="dim")
        table.add_column("Created", style="dim")
        for p in projects:
            table.add_row(p["id"][:8] + "...", p["name"], p.get("description") or "", p["created_at"][:10] if p.get("created_at") else "")
        console.print(table)
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
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
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_project(
    project_id: str = typer.Argument(help="Project ID"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get project details."""
    api = PlanAPI()
    try:
        with console.status("[dim]Working...[/dim]"):
            p = asyncio.run(api.get_project(project_id))
        if as_json:
            console.print(json.dumps(p, indent=2))
            return
        console.print(f"[bold]Name:[/bold] {p['name']}")
        console.print(f"[bold]ID:[/bold] {p['id']}")
        console.print(f"[bold]Description:[/bold] {p.get('description') or ''}")
        console.print(f"[bold]Created:[/bold] {p.get('created_at')}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
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
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("archive")
def archive_project(
    project_id: str = typer.Argument(help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Archive a project."""
    if not force:
        if not typer.confirm(f"Archive project {project_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    api = PlanAPI()
    try:
        asyncio.run(api.archive_project(project_id))
        console.print("[green]Project archived[/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("unarchive")
def unarchive_project(
    project_id: str = typer.Argument(help="Project ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Unarchive a project."""
    if not force:
        if not typer.confirm(f"Unarchive project {project_id}?"):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    api = PlanAPI()
    try:
        asyncio.run(api.unarchive_project(project_id))
        console.print("[green]Project unarchived[/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)
