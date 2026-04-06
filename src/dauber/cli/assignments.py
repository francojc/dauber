"""Assignments CLI sub-app — list, show, create, and update."""

from __future__ import annotations

from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.assignments import (
    create_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
)

assignments_app = typer.Typer(name="assignments", help="Manage Canvas assignments.")


@assignments_app.command("list")
@async_command
async def assignments_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """List all assignments for a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_assignments(ectx.client, course_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "name", "due_at", "points_possible", "published"],
    )


@assignments_app.command("show")
@async_command
async def assignments_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
) -> None:
    """Show details for a single assignment (includes rubric if attached)."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_assignment(ectx.client, course_id, assignment_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@assignments_app.command("create")
@async_command
async def assignments_create(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    name: str = typer.Argument(help="Assignment name."),
    points: Optional[float] = typer.Option(None, "--points", help="Points possible."),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO 8601)."),
    types: Optional[str] = typer.Option(
        None,
        "--types",
        help="Comma-separated submission types.",
    ),
    publish: bool = typer.Option(False, "--publish", help="Publish immediately."),
) -> None:
    """Create a new assignment."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    sub_types = [t.strip() for t in types.split(",")] if types else None
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_assignment(
            ectx.client,
            course_id,
            name,
            points_possible=points,
            due_at=due,
            submission_types=sub_types,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@assignments_app.command("update")
@async_command
async def assignments_update(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    points: Optional[float] = typer.Option(None, "--points", help="Points possible."),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO 8601)."),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
) -> None:
    """Update an existing assignment."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await update_assignment(
            ectx.client,
            course_id,
            assignment_id,
            name=name,
            points_possible=points,
            due_at=due,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)
