"""Rubrics CLI sub-app — list, show, and create rubrics."""

from __future__ import annotations

import json
from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.rubrics import (
    attach_rubric,
    create_rubric,
    get_rubric,
    list_rubrics,
    parse_rubric_csv,
)

rubrics_app = typer.Typer(name="rubrics", help="Manage Canvas rubrics.")


@rubrics_app.command("list")
@async_command
async def rubrics_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """List all rubrics for a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_rubrics(ectx.client, course_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "title", "points_possible", "criteria_count"],
    )


@rubrics_app.command("show")
@async_command
async def rubrics_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    rubric_id: str = typer.Argument(help="Rubric ID."),
) -> None:
    """Show a rubric by direct ID."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_rubric(ectx.client, course_id, rubric_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    if fmt.value == "json":
        format_output(data, fmt)
    else:
        typer.echo(f"Rubric: {data['title']} ({data['points_possible']} pts)")
        typer.echo("")
        for criterion in data.get("criteria", []):
            typer.echo(
                f"  {criterion['id']}: {criterion['description']}"
                f" ({criterion['points']} pts)"
            )
            for rating in criterion.get("ratings", []):
                typer.echo(f"    - {rating['description']}: {rating['points']} pts")


@rubrics_app.command("create")
@async_command
async def rubrics_create(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    file: str = typer.Option(..., "--file", "-f", help="Path to rubric JSON file."),
) -> None:
    """Create a rubric from a JSON file."""
    course = resolve_course(course)
    fmt = ctx.obj["format"]

    try:
        raw = open(file).read()  # noqa: WPS515
    except FileNotFoundError:
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)

    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON: {exc}", err=True)
        raise typer.Exit(1)

    title = spec.get("title", "")
    criteria = spec.get("criteria", [])

    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_rubric(ectx.client, course_id, title, criteria)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "title", "points_possible", "criteria_count"],
    )


@rubrics_app.command("import")
@async_command
async def rubrics_import(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    csv_path: str = typer.Option(..., "--csv", help="Path to Canvas rubric CSV file."),
) -> None:
    """Create a rubric from a Canvas-format CSV file."""
    try:
        title, criteria = parse_rubric_csv(csv_path)
    except FileNotFoundError:
        typer.echo(f"File not found: {csv_path}", err=True)
        raise typer.Exit(1)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    course = resolve_course(course)
    fmt = ctx.obj["format"]
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_rubric(ectx.client, course_id, title, criteria)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["id", "title", "points_possible", "criteria_count"],
    )


@rubrics_app.command("attach")
@async_command
async def rubrics_attach(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    rubric_id: str = typer.Argument(..., help="Rubric ID."),
    assignment_id: str = typer.Argument(..., help="Assignment ID."),
    use_for_grading: bool = typer.Option(
        False, "--use-for-grading", help="Map rubric scores to assignment grade."
    ),
) -> None:
    """Attach a rubric to an assignment."""
    course = resolve_course(course)
    fmt = ctx.obj["format"]
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await attach_rubric(
            ectx.client, course_id, rubric_id, assignment_id, use_for_grading
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        fmt,
        headers=["rubric_id", "assignment_id", "use_for_grading", "purpose"],
    )
