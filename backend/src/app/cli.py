"""Command-line interface for Scripe."""

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from app.logging_config import configure_logging, get_logger
from app.pipeline.runner import PipelineRunner
from app.storage.db import db
from app.storage.export import export_to_csv, export_to_jsonl
from app.storage.repo import CompanyRepository, RunRepository, SearchRepository

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create Typer app
app = typer.Typer(
    name="scripe",
    help="Scripe - B2B Lead Generation Platform (Compliance-First)",
    no_args_is_help=True,
)

# Rich console for pretty output
console = Console()


@app.command("init")
def init_database() -> None:
    """Initialize the database and create tables."""
    console.print("[bold blue]Initializing database...[/bold blue]")
    db.create_tables()
    console.print("[bold green]✓[/bold green] Database initialized successfully")


@app.command("search-create")
def create_search(
    name: Annotated[str, typer.Option("--name", "-n", help="Search name")],
    target_count: Annotated[int, typer.Option("--target", "-t", help="Target number of companies")] = 1000,
    country: Annotated[str, typer.Option("--country", "-c", help="Country code")] = "IT",
    regions: Annotated[str, typer.Option("--regions", "-r", help="Comma-separated regions")] = "",
    cities: Annotated[str, typer.Option("--cities", help="Comma-separated cities")] = "",
    categories: Annotated[str, typer.Option("--categories", help="Comma-separated categories")] = "",
    keywords_include: Annotated[str, typer.Option("--keywords", "-k", help="Comma-separated keywords to include")] = "",
    keywords_exclude: Annotated[str, typer.Option("--exclude", "-e", help="Comma-separated keywords to exclude")] = "",
    require_phone: Annotated[bool, typer.Option("--require-phone", help="Require phone number")] = True,
    require_website: Annotated[bool, typer.Option("--require-website", help="Require website")] = True,
) -> None:
    """Create a new search configuration."""

    # Parse comma-separated values
    regions_list = [r.strip() for r in regions.split(",") if r.strip()]
    cities_list = [c.strip() for c in cities.split(",") if c.strip()]
    categories_list = [c.strip() for c in categories.split(",") if c.strip()]
    keywords_include_list = [k.strip() for k in keywords_include.split(",") if k.strip()]
    keywords_exclude_list = [k.strip() for k in keywords_exclude.split(",") if k.strip()]

    # Build criteria
    criteria = {
        "country": country,
        "regions": regions_list,
        "cities": cities_list,
        "categories": categories_list,
        "keywords_include": keywords_include_list,
        "keywords_exclude": keywords_exclude_list,
        "require_phone": require_phone,
        "require_website": require_website,
        "min_match_score": 0.4,
        "min_confidence_score": 0.5,
    }

    # Create search
    with db.session() as session:
        search_repo = SearchRepository(session)
        search = search_repo.create(
            name=name,
            criteria=criteria,
            target_count=target_count,
        )
        session.commit()

        console.print(f"[bold green]✓[/bold green] Search created with ID: [bold]{search.id}[/bold]")
        console.print(f"  Name: {name}")
        console.print(f"  Target count: {target_count}")
        console.print(f"  Regions: {', '.join(regions_list) or 'None'}")
        console.print(f"  Categories: {', '.join(categories_list) or 'None'}")
        console.print(f"  Keywords include: {', '.join(keywords_include_list) or 'None'}")
        console.print(f"  Keywords exclude: {', '.join(keywords_exclude_list) or 'None'}")


@app.command("search-list")
def list_searches() -> None:
    """List all searches."""
    with db.session() as session:
        search_repo = SearchRepository(session)
        searches = search_repo.list_all()

        if not searches:
            console.print("[yellow]No searches found[/yellow]")
            return

        table = Table(title="Searches")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Target Count", justify="right")
        table.add_column("Created At")

        for search in searches:
            table.add_row(
                str(search.id),
                search.name,
                str(search.target_count),
                search.created_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)


@app.command("run-start")
def start_run(
    search_id: Annotated[int, typer.Argument(help="Search ID to run")],
) -> None:
    """Start a new run for a search."""
    console.print(f"[bold blue]Starting run for search ID {search_id}...[/bold blue]")

    try:
        # Run pipeline
        runner = PipelineRunner(db)
        result = asyncio.run(runner.run_search(search_id))

        console.print(f"[bold green]✓[/bold green] Run completed successfully")
        console.print(f"  Run ID: {result['run_id']}")
        console.print(f"  Status: {result['status']}")
        console.print(f"  Found: {result['found_count']}/{result['target_count']}")
        console.print(f"  Discarded: {result['discarded_count']}")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Run failed: {str(e)}")
        raise typer.Exit(1)


@app.command("run-status")
def show_run_status(
    run_id: Annotated[int, typer.Argument(help="Run ID")],
) -> None:
    """Show status of a run."""
    with db.session() as session:
        run_repo = RunRepository(session)
        run = run_repo.get_by_id(run_id)

        if not run:
            console.print(f"[red]Run {run_id} not found[/red]")
            raise typer.Exit(1)

        console.print(f"[bold]Run ID:[/bold] {run.id}")
        console.print(f"[bold]Search ID:[/bold] {run.search_id}")
        console.print(f"[bold]Status:[/bold] {run.status}")
        console.print(f"[bold]Started:[/bold] {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if run.ended_at:
            console.print(f"[bold]Ended:[/bold] {run.ended_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"[bold]Found:[/bold] {run.found_count}")
        console.print(f"[bold]Discarded:[/bold] {run.discarded_count}")

        if run.notes_json:
            console.print("\n[bold]Notes:[/bold]")
            console.print(json.dumps(run.notes_json, indent=2))


@app.command("export")
def export_results(
    search_id: Annotated[int, typer.Argument(help="Search ID to export")],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Output file path")] = Path("export.csv"),
    format: Annotated[str, typer.Option("--format", "-f", help="Export format (csv or jsonl)")] = "csv",
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Limit number of records")] = None,
) -> None:
    """Export search results to CSV or JSONL."""

    console.print(f"[bold blue]Exporting search {search_id} to {output_path}...[/bold blue]")

    try:
        with db.session() as session:
            company_repo = CompanyRepository(session)

            # Get companies
            companies = company_repo.get_top_by_score(
                search_id=search_id,
                limit=limit or 999999,
                min_match_score=0.0,
            )

            if not companies:
                console.print("[yellow]No companies found for this search[/yellow]")
                return

            # Export
            if format == "csv":
                export_to_csv(companies, output_path)
            elif format == "jsonl":
                export_to_jsonl(companies, output_path)
            else:
                console.print(f"[red]Unknown format: {format}[/red]")
                raise typer.Exit(1)

            console.print(f"[bold green]✓[/bold green] Exported {len(companies)} companies to {output_path}")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Export failed: {str(e)}")
        raise typer.Exit(1)


@app.command("stats")
def show_stats(
    search_id: Annotated[int, typer.Argument(help="Search ID")],
) -> None:
    """Show statistics for a search."""
    with db.session() as session:
        search_repo = SearchRepository(session)
        company_repo = CompanyRepository(session)

        search = search_repo.get_by_id(search_id)
        if not search:
            console.print(f"[red]Search {search_id} not found[/red]")
            raise typer.Exit(1)

        total_count = company_repo.count_by_search(search_id, min_quality=0.0)

        console.print(f"[bold]Search:[/bold] {search.name} (ID: {search.id})")
        console.print(f"[bold]Target count:[/bold] {search.target_count}")
        console.print(f"[bold]Total companies:[/bold] {total_count}")

        # Get top companies
        top_companies = company_repo.get_top_by_score(search_id, limit=10)

        if top_companies:
            console.print("\n[bold]Top 10 Companies:[/bold]")
            table = Table()
            table.add_column("Company Name", style="green")
            table.add_column("Match Score", justify="right")
            table.add_column("Confidence", justify="right")
            table.add_column("City")

            for company in top_companies:
                table.add_row(
                    company.company_name[:40],
                    f"{company.match_score:.2f}",
                    f"{company.confidence_score:.2f}",
                    company.city or "N/A",
                )

            console.print(table)


if __name__ == "__main__":
    app()
