"""Pages CLI sub-app — list, show, create, update, and delete."""

from __future__ import annotations

from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.pages import (
    create_page,
    delete_page,
    get_page,
    list_pages,
    update_page,
)

pages_app = typer.Typer(name="pages", help="Manage Canvas course pages.")


@pages_app.command("list")
@async_command
async def pages_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    published: Optional[bool] = typer.Option(
        None,
        "--published/--unpublished",
        help="Filter by publish status.",
    ),
    search: Optional[str] = typer.Option(
        None, "--search", help="Filter by search term."
    ),
    sort: str = typer.Option(
        "title", "--sort", help="Sort field (title, created_at, updated_at)."
    ),
) -> None:
    """List all pages for a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_pages(
            ectx.client,
            course_id,
            published=published,
            search_term=search,
            sort=sort,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["url", "title", "published", "updated_at"],
    )


@pages_app.command("show")
@async_command
async def pages_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    page_url: str = typer.Argument(help="Page URL slug."),
) -> None:
    """Show details for a single page."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_page(ectx.client, course_id, page_url)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@pages_app.command("create")
@async_command
async def pages_create(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    title: str = typer.Argument(help="Page title."),
    body: str = typer.Option("", "--body", help="Page body content."),
    publish: bool = typer.Option(False, "--publish", help="Publish immediately."),
    front_page: bool = typer.Option(False, "--front-page", help="Set as front page."),
    editing_roles: Optional[str] = typer.Option(
        None, "--editing-roles", help="Editing roles (e.g. teachers)."
    ),
) -> None:
    """Create a new page."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_page(
            ectx.client,
            course_id,
            title,
            body,
            published=publish,
            front_page=front_page,
            editing_roles=editing_roles,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@pages_app.command("update")
@async_command
async def pages_update(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    page_url: str = typer.Argument(help="Page URL slug."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    body: Optional[str] = typer.Option(None, "--body", help="New body content."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
) -> None:
    """Update an existing page."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await update_page(
            ectx.client,
            course_id,
            page_url,
            title=title,
            body=body,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@pages_app.command("delete")
@async_command
async def pages_delete(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    page_url: str = typer.Argument(help="Page URL slug."),
) -> None:
    """Delete a page."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await delete_page(ectx.client, course_id, page_url)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    typer.echo(f"Deleted page {data['url']}.")
