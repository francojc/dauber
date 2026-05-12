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
    create_module_item,
    delete_module,
    delete_module_item,
    get_module,
    get_module_item,
    list_module_items,
    list_modules,
    update_module,
    update_module_item,
)

modules_app = typer.Typer(name="modules", help="Manage Canvas course modules.")
items_app = typer.Typer(name="items", help="Manage items within Canvas modules.")
modules_app.add_typer(items_app)

_ITEM_TYPES = {"Page", "Assignment", "Discussion", "File", "ExternalUrl", "SubHeader"}


def _validate_item_create(
    item_type: str,
    content_id: str | None,
    page_url: str | None,
    url: str | None,
) -> None:
    if item_type not in _ITEM_TYPES:
        raise typer.BadParameter(
            f"type must be one of: {', '.join(sorted(_ITEM_TYPES))}"
        )
    if item_type == "Page" and not page_url:
        raise typer.BadParameter("--page-url is required for Page items")
    if item_type in {"Assignment", "Discussion", "File"} and not content_id:
        raise typer.BadParameter(f"--content-id is required for {item_type} items")
    if item_type == "ExternalUrl" and not url:
        raise typer.BadParameter("--url is required for ExternalUrl items")


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


@items_app.command("list")
@async_command
async def module_items_list(
    ctx: typer.Context,
    module_id: str = typer.Argument(help="Module ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """List items in a module."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_module_items(ectx.client, course_id, module_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "title", "type", "position", "indent", "published"],
    )


@items_app.command("show")
@async_command
async def module_items_show(
    ctx: typer.Context,
    module_id: str = typer.Argument(help="Module ID."),
    item_id: str = typer.Argument(help="Module item ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """Show a module item."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_module_item(ectx.client, course_id, module_id, item_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@items_app.command("create")
@async_command
async def module_items_create(
    ctx: typer.Context,
    module_id: str = typer.Argument(help="Module ID."),
    title: str = typer.Argument(help="Item title."),
    item_type: str = typer.Option(..., "--type", help="Item type."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    content_id: Optional[str] = typer.Option(
        None,
        "--content-id",
        help="Canvas content ID for Assignment, Discussion, or File.",
    ),
    page_url: Optional[str] = typer.Option(
        None, "--page-url", help="Canvas page URL slug for Page items."
    ),
    url: Optional[str] = typer.Option(None, "--url", help="URL for ExternalUrl items."),
    indent: Optional[int] = typer.Option(None, "--indent", help="Indent level."),
    position: Optional[int] = typer.Option(None, "--position", help="Position."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
    new_tab: Optional[bool] = typer.Option(
        None, "--new-tab/--same-tab", help="Open ExternalUrl in new tab."
    ),
) -> None:
    """Create a module item."""
    _validate_item_create(item_type, content_id, page_url, url)
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_module_item(
            ectx.client,
            course_id,
            module_id,
            title,
            item_type,
            content_id=content_id,
            page_url=page_url,
            url=url,
            indent=indent,
            position=position,
            published=publish,
            new_tab=new_tab,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@items_app.command("update")
@async_command
async def module_items_update(
    ctx: typer.Context,
    module_id: str = typer.Argument(help="Module ID."),
    item_id: str = typer.Argument(help="Module item ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    indent: Optional[int] = typer.Option(None, "--indent", help="Indent level."),
    position: Optional[int] = typer.Option(None, "--position", help="Position."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
) -> None:
    """Update a module item."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await update_module_item(
            ectx.client,
            course_id,
            module_id,
            item_id,
            title=title,
            indent=indent,
            position=position,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@items_app.command("delete")
@async_command
async def module_items_delete(
    ctx: typer.Context,
    module_id: str = typer.Argument(help="Module ID."),
    item_id: str = typer.Argument(help="Module item ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """Delete a module item."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await delete_module_item(ectx.client, course_id, module_id, item_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    typer.echo(f"Deleted module item {data['id']}.")
