"""Discussions CLI sub-app — list, show, create, and update."""

from __future__ import annotations

from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.discussions import (
    create_discussion,
    get_discussion,
    list_discussions,
    update_discussion,
)

discussions_app = typer.Typer(
    name="discussions", help="Manage Canvas discussion topics."
)


@discussions_app.command("list")
@async_command
async def discussions_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    announcements: bool = typer.Option(
        False, "--announcements", help="Show only announcements."
    ),
) -> None:
    """List all discussion topics for a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_discussions(
            ectx.client,
            course_id,
            only_announcements=announcements,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "title", "published", "posted_at", "is_announcement"],
    )


@discussions_app.command("show")
@async_command
async def discussions_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    topic_id: str = typer.Argument(help="Discussion topic ID."),
) -> None:
    """Show details for a single discussion topic."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_discussion(ectx.client, course_id, topic_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@discussions_app.command("create")
@async_command
async def discussions_create(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    title: str = typer.Argument(help="Discussion title."),
    message: str = typer.Option("", "--message", help="Discussion body."),
    announcement: bool = typer.Option(
        False, "--announcement", help="Create as announcement."
    ),
    publish: bool = typer.Option(False, "--publish", help="Publish immediately."),
    pinned: bool = typer.Option(False, "--pinned", help="Pin the topic."),
) -> None:
    """Create a new discussion topic."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_discussion(
            ectx.client,
            course_id,
            title,
            message,
            is_announcement=announcement,
            published=publish,
            pinned=pinned,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@discussions_app.command("update")
@async_command
async def discussions_update(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    topic_id: str = typer.Argument(help="Discussion topic ID."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    message: Optional[str] = typer.Option(None, "--message", help="New message body."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
    pinned: Optional[bool] = typer.Option(None, "--pin/--unpin", help="Pin or unpin."),
) -> None:
    """Update an existing discussion topic."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await update_discussion(
            ectx.client,
            course_id,
            topic_id,
            title=title,
            message=message,
            published=publish,
            pinned=pinned,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)
