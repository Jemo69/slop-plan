import asyncio
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from plan_cli.api import PlanAPI, PlanAPIError
from plan_cli.frontmatter import parse_frontmatter

console = Console()
app = typer.Typer(help="Plan commands")


@app.command()
def create(
    project_id: str = typer.Option(..., "--project", "-p", help="Project ID"),
    title: str = typer.Option(..., "--title", "-t", help="Plan title"),
    html_file: Path = typer.Option(..., "--html", help="HTML file path"),
    public: bool = typer.Option(False, "--public", help="Make plan public"),
):
    """Create a new plan from an HTML file."""
    if not html_file.exists():
        console.print(f"[red]File not found: {html_file}[/red]")
        raise typer.Exit(1)
    
    html_content = html_file.read_text()
    frontmatter, content = parse_frontmatter(html_content)
    
    if frontmatter.get("title"):
        title = frontmatter["title"]
    if frontmatter.get("visibility") == "public":
        public = True
    
    api = PlanAPI()
    
    try:
        result = asyncio.run(api.create_plan(
            project_id=project_id,
            title=title,
            html_content=content,
            frontmatter=frontmatter,
            is_public=public,
        ))
        console.print(f"[green]Plan created successfully![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"Slug: {result['slug']}")
        console.print(f"URL: [link]{result['url']}[/link]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_plans(
    project_id: str = typer.Option(None, "--project", "-p", help="Filter by project ID"),
):
    """List all plans."""
    api = PlanAPI()
    
    try:
        plans = asyncio.run(api.list_plans(project_id=project_id))
        
        if not plans:
            console.print("[yellow]No plans found.[/yellow]")
            return
        
        table = Table(title="Plans")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("URL", style="blue")
        table.add_column("Public", justify="center")
        table.add_column("Updated", style="dim")
        
        for plan in plans:
            table.add_row(
                plan["id"][:8] + "...",
                plan["title"],
                plan["url"],
                "✓" if plan["is_public"] else "✗",
                plan["updated_at"][:10],
            )
        
        console.print(table)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def get(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    """Get plan details."""
    api = PlanAPI()
    
    try:
        plan = asyncio.run(api.get_plan(plan_id))
        
        console.print(f"[bold]Title:[/bold] {plan['title']}")
        console.print(f"[bold]ID:[/bold] {plan['id']}")
        console.print(f"[bold]URL:[/bold] [link]{plan['url']}[/link]")
        console.print(f"[bold]Public:[/bold] {'Yes' if plan['is_public'] else 'No'}")
        console.print(f"[bold]Created:[/bold] {plan['created_at']}")
        console.print(f"[bold]Updated:[/bold] {plan['updated_at']}")
        
        if plan.get("frontmatter"):
            console.print("\n[bold]Frontmatter:[/bold]")
            for key, value in plan["frontmatter"].items():
                console.print(f"  {key}: {value}")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    plan_id: str = typer.Argument(help="Plan ID"),
    html_file: Path = typer.Option(None, "--html", help="HTML file path"),
    title: str = typer.Option(None, "--title", "-t", help="Plan title"),
):
    """Update an existing plan."""
    api = PlanAPI()
    updates = {}
    
    if html_file:
        if not html_file.exists():
            console.print(f"[red]File not found: {html_file}[/red]")
            raise typer.Exit(1)
        
        html_content = html_file.read_text()
        frontmatter, content = parse_frontmatter(html_content)
        updates["html_content"] = content
        if frontmatter:
            updates["frontmatter"] = frontmatter
    
    if title:
        updates["title"] = title
    
    if not updates:
        console.print("[yellow]Nothing to update.[/yellow]")
        return
    
    try:
        result = asyncio.run(api.update_plan(plan_id, **updates))
        console.print(f"[green]Plan updated successfully![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"URL: [link]{result['url']}[/link]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    plan_id: str = typer.Argument(help="Plan ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a plan."""
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete plan {plan_id}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)
    
    api = PlanAPI()
    
    try:
        asyncio.run(api.delete_plan(plan_id))
        console.print(f"[green]Plan deleted successfully![/green]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def publish(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    """Make a plan public."""
    api = PlanAPI()
    
    try:
        result = asyncio.run(api.publish_plan(plan_id))
        console.print(f"[green]Plan published![/green]")
        console.print(f"URL: [link]{result['url']}[/link]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def unpublish(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    """Make a plan private."""
    api = PlanAPI()
    
    try:
        result = asyncio.run(api.unpublish_plan(plan_id))
        console.print(f"[green]Plan unpublished![/green]")
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)
