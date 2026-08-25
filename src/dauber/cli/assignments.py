"""Assignments CLI sub-app — list, show, create, and update."""

from __future__ import annotations

from typing import Optional

from dateutil.parser import isoparse
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


def _validate_availability_dates(
    unlock_at: str | None,
    due_at: str | None,
    lock_at: str | None,
) -> None:
    """Validate supplied ISO 8601 assignment dates and their ordering."""
    parsed_dates = []
    for name, value in (
        ("unlock-at", unlock_at),
        ("due", due_at),
        ("lock-at", lock_at),
    ):
        if value is None:
            continue
        try:
            parsed_dates.append((name, isoparse(value)))
        except (TypeError, ValueError, OverflowError) as exc:
            raise typer.BadParameter(
                f"--{name} must be an ISO 8601 date or datetime."
            ) from exc

    try:
        for (_, earlier), (_, later) in zip(parsed_dates, parsed_dates[1:]):
            if earlier > later:
                raise typer.BadParameter(
                    "Availability dates must satisfy --unlock-at <= --due <= --lock-at."
                )
    except TypeError as exc:
        raise typer.BadParameter(
            "Availability dates must consistently include or omit timezone offsets."
        ) from exc


def _validate_clear_flags(
    unlock_at: str | None,
    due_at: str | None,
    lock_at: str | None,
    clear_unlock_at: bool,
    clear_due_at: bool,
    clear_lock_at: bool,
) -> None:
    """Reject setting and clearing an availability date in one update."""
    for option, value, clear_option, clear in (
        ("--unlock-at", unlock_at, "--clear-unlock-at", clear_unlock_at),
        ("--due", due_at, "--clear-due-at", clear_due_at),
        ("--lock-at", lock_at, "--clear-lock-at", clear_lock_at),
    ):
        if value is not None and clear:
            raise typer.BadParameter(f"{option} cannot be used with {clear_option}.")


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
        headers=[
            "id",
            "name",
            "assignment_group_name",
            "unlock_at",
            "due_at",
            "lock_at",
            "points_possible",
            "published",
        ],
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
    unlock_at: Optional[str] = typer.Option(
        None, "--unlock-at", help="Availability start (ISO 8601)."
    ),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO 8601)."),
    lock_at: Optional[str] = typer.Option(
        None, "--lock-at", help="Availability end (ISO 8601)."
    ),
    types: Optional[str] = typer.Option(
        None,
        "--types",
        help="Comma-separated submission types.",
    ),
    publish: bool = typer.Option(False, "--publish", help="Publish immediately."),
) -> None:
    """Create a new assignment."""
    _validate_availability_dates(unlock_at, due, lock_at)
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
            unlock_at=unlock_at,
            due_at=due,
            lock_at=lock_at,
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
    unlock_at: Optional[str] = typer.Option(
        None, "--unlock-at", help="Availability start (ISO 8601)."
    ),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (ISO 8601)."),
    lock_at: Optional[str] = typer.Option(
        None, "--lock-at", help="Availability end (ISO 8601)."
    ),
    clear_unlock_at: bool = typer.Option(
        False, "--clear-unlock-at", help="Remove availability start."
    ),
    clear_due_at: bool = typer.Option(False, "--clear-due-at", help="Remove due date."),
    clear_lock_at: bool = typer.Option(
        False, "--clear-lock-at", help="Remove availability end."
    ),
    publish: Optional[bool] = typer.Option(
        None, "--publish/--unpublish", help="Publish or unpublish."
    ),
) -> None:
    """Update an existing assignment."""
    _validate_availability_dates(unlock_at, due, lock_at)
    _validate_clear_flags(
        unlock_at,
        due,
        lock_at,
        clear_unlock_at,
        clear_due_at,
        clear_lock_at,
    )
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
            unlock_at=unlock_at,
            due_at=due,
            lock_at=lock_at,
            clear_unlock_at=clear_unlock_at,
            clear_due_at=clear_due_at,
            clear_lock_at=clear_lock_at,
            published=publish,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)
