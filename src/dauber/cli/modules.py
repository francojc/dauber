"""Modules CLI sub-app — list, show, create, update, and delete."""

from __future__ import annotations

from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.modules import (
    create_module,
    delete_module,
    get_module,
    list_modules,
    update_module,
)

modules_app = typer.Typer(name="modules", help="Manage Canvas course modules.")


@modules_app.command("list")
@async_command
async def modules_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    items: bool = typer.Option(False, "--items", help="Include module items."),
    search: Optional[str] = typer.Option(
        None, "--search", help="Filter by search term."
    ),
) -> None:
    """List all modules for a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_modules(
            ectx.client,
            course_id,
            include_items=items,
            search_term=search,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "name", "position", "published", "items_count"],
    )


@modules_app.command("show")
@async_command
async def modules_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    module_id: str = typer.Argument(help="Module ID."),
) -> None:
    """Show details for a single module with its items."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_module(ectx.client, course_id, module_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@modules_app.command("create")
@async_command
async def modules_create(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    name: str = typer.Argument(help="Module name."),
    position: Optional[int] = typer.Option(
        None, "--position", help="Position in module list."
    ),
    unlock_at: Optional[str] = typer.Option(
        None, "--unlock-at", help="Unlock date (ISO 8601)."
    ),
    sequential: bool = typer.Option(
        False, "--sequential", help="Require sequential progress."
    ),
    publish: bool = typer.Option(False, "--publish", help="Publish immediately."),
) -> None:
    """Create a new module."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_module(
            ectx.client,
            course_id,
            name,
            position=position,
            unlock_at=unlock_at,
            require_sequential_progress=sequential,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@modules_app.command("update")
@async_command
async def modules_update(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    module_id: str = typer.Argument(help="Module ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    position: Optional[int] = typer.Option(None, "--position", help="New position."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
) -> None:
    """Update an existing module."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await update_module(
            ectx.client,
            course_id,
            module_id,
            name=name,
            position=position,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@modules_app.command("delete")
@async_command
async def modules_delete(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    module_id: str = typer.Argument(help="Module ID."),
) -> None:
    """Delete a module."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await delete_module(ectx.client, course_id, module_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    typer.echo(f"Deleted module {data['id']}.")
