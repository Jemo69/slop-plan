import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.status import Status
from plan_cli.api import PlanAPI, PlanAPIError, PlanConnectionError
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
        console.print("[green]Plan created successfully![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"Slug: {result['slug']}")
        console.print(f"URL: [link]{result['url']}[/link]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_plans(
    project_id: str = typer.Option(None, "--project", "-p", help="Filter by project ID"),
    public: bool = typer.Option(False, "--public", help="List only public plans"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    limit: int = typer.Option(None, "--limit", "-n", help="Max results to show"),
    offset: int = typer.Option(0, "--offset", help="Skip first N results"),
):
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            if public:
                plans = asyncio.run(api.list_public_plans())
            else:
                plans = asyncio.run(api.list_plans(project_id=project_id))

        if not plans:
            console.print("[yellow]No plans found.[/yellow]")
            return

        total = len(plans)
        plans = plans[offset:]
        if limit is not None:
            plans = plans[:limit]

        if as_json:
            console.print(json.dumps(plans, indent=2))
            return

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
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            plan = asyncio.run(api.get_plan(plan_id))

        if as_json:
            console.print(json.dumps(plan, indent=2))
            return

        console.print(f"[bold]Title:[/bold] {plan['title']}")
        console.print(f"[bold]ID:[/bold] {plan['id']}")
        console.print(f"[bold]Project:[/bold] {plan.get('project_id','')}")
        console.print(f"[bold]URL:[/bold] [link]{plan['url']}[/link]")
        console.print(f"[bold]Public:[/bold] {'Yes' if plan['is_public'] else 'No'}")
        console.print(f"[bold]Created:[/bold] {plan['created_at']}")
        console.print(f"[bold]Updated:[/bold] {plan['updated_at']}")

        if plan.get("frontmatter"):
            console.print("\n[bold]Frontmatter:[/bold]")
            for key, value in plan["frontmatter"].items():
                console.print(f"  {key}: {value}")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    plan_id: str = typer.Argument(help="Plan ID"),
    html_file: Optional[Path] = typer.Option(None, "--html", help="HTML file path"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Plan title"),
):
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
        console.print("[yellow]Nothing to update. Provide --html or --title.[/yellow]")
        raise typer.Exit(1)

    try:
        result = asyncio.run(api.update_plan(plan_id, **updates))
        console.print("[green]Plan updated successfully![/green]")
        console.print(f"ID: [bold]{result['id']}[/bold]")
        console.print(f"URL: [link]{result['url']}[/link]")
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
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete plan {plan_id}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    api = PlanAPI()

    try:
        asyncio.run(api.delete_plan(plan_id))
        console.print("[green]Plan deleted successfully![/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def publish(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    api = PlanAPI()

    try:
        result = asyncio.run(api.publish_plan(plan_id))
        console.print("[green]Plan published![/green]")
        console.print(f"URL: [link]{result['url']}[/link]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def unpublish(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    api = PlanAPI()

    try:
        result = asyncio.run(api.unpublish_plan(plan_id))
        console.print("[green]Plan unpublished![/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def archive(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    """Archive a plan."""
    api = PlanAPI()

    try:
        asyncio.run(api.archive_plan(plan_id))
        console.print("[green]Plan archived![/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


@app.command()
def unarchive(
    plan_id: str = typer.Argument(help="Plan ID"),
):
    """Unarchive a plan."""
    api = PlanAPI()

    try:
        asyncio.run(api.unarchive_plan(plan_id))
        console.print("[green]Plan unarchived![/green]")
    except PlanConnectionError:
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
        raise typer.Exit(1)
    except PlanAPIError as e:
        console.print(f"[red]Error: {e.detail}[/red]")
        raise typer.Exit(1)


def _handle_api_error(exc, api):
    """Shared error rendering for the version commands."""
    if isinstance(exc, PlanConnectionError):
        console.print(f"[red]Cannot connect to {api.base_url}. Is the server running?[/red]")
    else:
        console.print(f"[red]Error: {exc.detail}[/red]")
    raise typer.Exit(1)


@app.command("versions")
def versions(
    plan_id: str = typer.Argument(help="Plan ID"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List a plan's version history, newest first."""
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.list_versions(plan_id))
    except (PlanConnectionError, PlanAPIError) as e:
        _handle_api_error(e, api)

    if as_json:
        console.print(json.dumps(result, indent=2))
        return

    if result.get("versioning_available") is False:
        console.print(
            "[yellow]Version history is not enabled on this server yet.[/yellow]"
        )
        return

    entries = result.get("versions", [])
    if not entries:
        console.print("[yellow]No previous versions yet.[/yellow]")
        console.print("[dim]A version is recorded automatically when you update a plan.[/dim]")
        return

    table = Table(title=f"Version history for {plan_id[:8]}...")
    table.add_column("Version", style="cyan", justify="right")
    table.add_column("Title", style="green")
    table.add_column("Note", style="magenta")
    table.add_column("Size", justify="right", style="dim")
    table.add_column("Created", style="dim")

    for entry in entries:
        table.add_row(
            f"v{entry['version']}",
            entry.get("title", ""),
            entry.get("note") or "-",
            f"{entry.get('size_bytes', 0):,}B",
            (entry.get("created_at") or "")[:19].replace("T", " "),
        )

    console.print(table)
    console.print("[dim]Restore with:[/dim] plan plans restore <plan-id> <version>")


@app.command("version")
def show_version(
    plan_id: str = typer.Argument(help="Plan ID"),
    version: int = typer.Argument(help="Version number"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    to_file: Optional[Path] = typer.Option(None, "--out", help="Write HTML to a file"),
):
    """Show the full content of one version."""
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.get_version(plan_id, version))
    except (PlanConnectionError, PlanAPIError) as e:
        _handle_api_error(e, api)

    if to_file:
        to_file.write_text(result["html_content"])
        console.print(f"[green]Wrote v{version} to[/green] {to_file}")
        return

    if as_json:
        console.print(json.dumps(result, indent=2))
        return

    console.print(f"[bold]Version:[/bold] v{result['version']}")
    console.print(f"[bold]Title:[/bold] {result['title']}")
    console.print(f"[bold]Created:[/bold] {result['created_at']}")
    if result.get("note"):
        console.print(f"[bold]Note:[/bold] {result['note']}")
    console.print(f"\n[bold]Content[/bold] ({result.get('size_bytes', 0):,} bytes):")
    console.print(result["html_content"])


@app.command("snapshot")
def snapshot(
    plan_id: str = typer.Argument(help="Plan ID"),
    note: Optional[str] = typer.Option(None, "--note", "-m", help="Label for this snapshot"),
):
    """Snapshot the plan's current content with an optional note."""
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.create_snapshot(plan_id, note=note))
    except (PlanConnectionError, PlanAPIError) as e:
        _handle_api_error(e, api)

    console.print(f"[green]Snapshot saved as v{result['version']}[/green]")
    if note:
        console.print(f"Note: {note}")


@app.command()
def restore(
    plan_id: str = typer.Argument(help="Plan ID"),
    version: int = typer.Argument(help="Version number to restore"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Roll a plan back to a previous version (reversible)."""
    if not force:
        confirm = typer.confirm(f"Restore {plan_id[:8]}... to v{version}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(api.restore_version(plan_id, version))
    except (PlanConnectionError, PlanAPIError) as e:
        _handle_api_error(e, api)

    console.print(f"[green]Restored to v{version}[/green]")
    console.print(f"Title: {result['title']}")
    console.print(f"URL: [link]{result['url']}[/link]")
    console.print("[dim]The previous content was saved, so this is reversible.[/dim]")


@app.command()
def diff(
    plan_id: str = typer.Argument(help="Plan ID"),
    from_version: Optional[int] = typer.Option(None, "--from", help="Source version"),
    to_version: Optional[int] = typer.Option(None, "--to", help="Target version"),
):
    """Diff two versions, or a version against the live plan."""
    api = PlanAPI()

    try:
        with console.status("[dim]Working...[/dim]"):
            result = asyncio.run(
                api.diff_versions(plan_id, from_version, to_version)
            )
    except (PlanConnectionError, PlanAPIError) as e:
        _handle_api_error(e, api)

    if not result.get("changed"):
        console.print("[yellow]No differences.[/yellow]")
        return

    label_from = f"v{from_version}" if from_version else "current"
    label_to = f"v{to_version}" if to_version else "current"

    console.print(
        f"[bold]{label_from} -> {label_to}[/bold]  "
        f"[green]+{result['added']}[/green] [red]-{result['removed']}[/red]\n"
    )
    for line in result["diff"].splitlines():
        if line.startswith("+++") or line.startswith("---"):
            console.print(f"[bold]{line}[/bold]")
        elif line.startswith("+"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(f"[dim]{line}[/dim]")
