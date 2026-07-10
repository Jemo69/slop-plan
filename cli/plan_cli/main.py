import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.status import Status

from plan_cli.commands.auth import app as auth_app
from plan_cli.commands.plans import app as plans_app
from plan_cli.commands.projects import app as projects_app
from plan_cli.commands.config_cmd import app as config_app
from plan_cli.api import PlanAPI, PlanAPIError, PlanConnectionError
from plan_cli.frontmatter import parse_frontmatter

console = Console()

app = typer.Typer(
    name="plan",
    help="HTML Plan Service CLI - Create, manage, and share HTML plans",
    no_args_is_help=True,
)

app.add_typer(auth_app, name="auth", help="Authentication commands")
app.add_typer(plans_app, name="plans", help="Plan management")
app.add_typer(projects_app, name="projects", help="Project management")
app.add_typer(config_app, name="config", help="Configuration")


@app.command()
def version():
    from plan_cli import __version__
    typer.echo(f"plan CLI v{__version__}")


@app.command()
def create(
    project: str = typer.Option(..., "--project", "-p", help="Project ID"),
    title: str = typer.Option(..., "--title", "-t", help="Plan title"),
    html: Path = typer.Option(..., "--html", help="HTML file path"),
    public: bool = typer.Option(False, "--public", help="Make plan public"),
):
    """Create a new plan (top-level alias)."""
    if not html.exists():
        console.print(f"[red]File not found: {html}[/red]")
        raise typer.Exit(1)
    html_content = html.read_text()
    frontmatter, content = parse_frontmatter(html_content)
    if frontmatter.get("title"):
        title = frontmatter["title"]
    if frontmatter.get("visibility") == "public":
        public = True
    api = PlanAPI()
    try:
        result = asyncio.run(api.create_plan(
            project_id=project, title=title, html_content=content,
            frontmatter=frontmatter, is_public=public,
        ))
        console.print("[green]Plan created![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"Slug: {result['slug']}")
        console.print(f"URL: {result['url']}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command(name="list")
def list_top(
    project: str = typer.Option(None, "--project", "-p", help="Filter by project ID"),
    public: bool = typer.Option(False, "--public", help="Public only"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    limit: int = typer.Option(None, "--limit", "-n", help="Max results to show"),
    offset: int = typer.Option(0, "--offset", help="Skip first N results"),
):
    """List plans (top-level alias)."""
    api = PlanAPI()
    try:
        with console.status("[dim]Working...[/dim]"):
            if public:
                plans = asyncio.run(api.list_public_plans())
            else:
                plans = asyncio.run(api.list_plans(project_id=project))
        if not plans:
            console.print("[yellow]No plans found.[/yellow]")
            return
        if as_json:
            console.print(json.dumps(plans, indent=2))
            return
        total = len(plans)
        plans = plans[offset:]
        if limit is not None:
            plans = plans[:limit]
        table = Table(title=f"Plans ({offset+1}-{min(offset+len(plans), total)} of {total})")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("URL", style="blue")
        table.add_column("Public", justify="center")
        table.add_column("Updated", style="dim")
        for plan in plans:
            table.add_row(
                plan["id"][:8] + "...",
                plan["title"],
                plan.get("url", plan.get("slug", "")),
                "✓" if plan.get("is_public") else "✗",
                plan.get("updated_at", "")[:10],
            )
        console.print(table)
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def get(
    plan_id: str = typer.Argument(help="Plan ID"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get plan details (top-level alias)."""
    api = PlanAPI()
    try:
        with console.status("[dim]Working...[/dim]"):
            plan = asyncio.run(api.get_plan(plan_id))
        if as_json:
            console.print(json.dumps(plan, indent=2))
            return
        console.print(f"[bold]Title:[/bold] {plan['title']}")
        console.print(f"[bold]ID:[/bold] {plan['id']}")
        console.print(f"[bold]URL:[/bold] {plan['url']}")
        console.print(f"[bold]Public:[/bold] {'Yes' if plan['is_public'] else 'No'}")
        console.print(f"[bold]Created:[/bold] {plan['created_at']}")
        console.print(f"[bold]Updated:[/bold] {plan['updated_at']}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    plan_id: str = typer.Argument(help="Plan ID"),
    html: Optional[Path] = typer.Option(None, "--html", help="HTML file path"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Plan title"),
):
    """Update a plan (top-level alias)."""
    api = PlanAPI()
    updates = {}
    if html:
        if not html.exists():
            console.print(f"[red]File not found: {html}[/red]")
            raise typer.Exit(1)
        html_content = html.read_text()
        frontmatter, content = parse_frontmatter(html_content)
        updates["html_content"] = content
        if frontmatter:
            updates["frontmatter"] = frontmatter
    if title:
        updates["title"] = title
    if not updates:
        console.print("[yellow]Nothing to update. Provide --html or --title.[/yellow]")
        raise typer.Exit(1)
    try:
        result = asyncio.run(api.update_plan(plan_id, **updates))
        console.print("[green]Plan updated![/green]")
        console.print(f"ID: {result['id']}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    plan_id: str = typer.Argument(help="Plan ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a plan (top-level alias)."""
    if not force and not typer.confirm(f"Delete plan {plan_id}?"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)
    api = PlanAPI()
    try:
        asyncio.run(api.delete_plan(plan_id))
        console.print("[green]Plan deleted[/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def publish(plan_id: str = typer.Argument(help="Plan ID")):
    """Make plan public (top-level alias)."""
    api = PlanAPI()
    try:
        result = asyncio.run(api.publish_plan(plan_id))
        console.print(f"[green]Published! URL: {result['url']}[/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def unpublish(plan_id: str = typer.Argument(help="Plan ID")):
    """Make plan private (top-level alias)."""
    api = PlanAPI()
    try:
        asyncio.run(api.unpublish_plan(plan_id))
        console.print("[green]Unpublished[/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    email: str = typer.Option(None, "--email", "-e", help="Your email"),
    api_url: str = typer.Option(None, "--api-url", help="API URL"),
):
    """Initialize CLI (shortcut for auth init)."""
    from plan_cli.config import set_api_key, set_api_url, get_api_url as _get_url, set_email
    if not email:
        email = typer.prompt("Your email")
    if api_url:
        set_api_url(api_url)
    else:
        set_api_url(_get_url())
    api = PlanAPI()
    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.register(email))
        set_api_key(result["api_key"])
        set_email(email)
        console.print("[green]Registered![/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        if "already registered" in str(e.detail).lower():
            console.print("[yellow]Already registered, logging in...[/yellow]")
            try:
                with console.status("[dim]Working...[/dim]"):
                    result = asyncio.run(api.login(email))
                set_api_key(result["api_key"])
                set_email(email)
                console.print("[green]Logged in![/green]")
            except PlanConnectionError:
                console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
                raise typer.Exit(1)
            except PlanAPIError as e2:
                console.print(f"[red]Error: {e2.detail}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Error: {e.detail}[/red]")
            raise typer.Exit(1)


if __name__ == "__main__":
    app()
