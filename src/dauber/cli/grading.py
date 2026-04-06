"""Grading CLI sub-app — submissions, grading, and rubric grading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_anonymize, resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.grading import (
    get_submission,
    list_submissions,
    submit_grade,
    submit_rubric_grade,
)

grading_app = typer.Typer(
    name="grading",
    help="View submissions and post grades.",
)


@grading_app.command("submissions")
@async_command
async def grading_submissions(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    anonymize: Optional[bool] = typer.Option(
        None,
        "--anonymize/--no-anonymize",
        help="Strip PII (user_name) for FERPA compliance.",
    ),
) -> None:
    """List all submissions for an assignment."""
    course = resolve_course(course)
    anonymize = resolve_anonymize(anonymize)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_submissions(
            ectx.client, course_id, assignment_id, anonymize=anonymize
        )
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
            "user_id",
            "user_name",
            "workflow_state",
            "score",
            "submitted_at",
        ],
    )


@grading_app.command("show")
@async_command
async def grading_show(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    user_id: str = typer.Argument(help="User ID."),
    anonymize: Optional[bool] = typer.Option(
        None,
        "--anonymize/--no-anonymize",
        help="Strip PII (user_name) for FERPA compliance.",
    ),
) -> None:
    """Show a single submission with rubric assessment detail."""
    course = resolve_course(course)
    anonymize = resolve_anonymize(anonymize)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_submission(
            ectx.client,
            course_id,
            assignment_id,
            user_id,
            anonymize=anonymize,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@grading_app.command("submit")
@async_command
async def grading_submit(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    user_id: str = typer.Argument(help="User ID."),
    grade: str = typer.Argument(help="Grade value (points or letter)."),
    comment: Optional[str] = typer.Option(
        None, "--comment", help="Submission comment."
    ),
) -> None:
    """Submit a simple grade for a submission."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await submit_grade(
            ectx.client,
            course_id,
            assignment_id,
            user_id,
            grade,
            comment=comment,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)


@grading_app.command("submit-rubric")
@async_command
async def grading_submit_rubric(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    user_id: str = typer.Argument(help="User ID."),
    assessment_file: str = typer.Argument(
        help="Path to a JSON file containing the rubric assessment.",
    ),
    comment: Optional[str] = typer.Option(
        None, "--comment", help="Overall submission comment."
    ),
) -> None:
    """Submit a rubric-based grade for a submission."""
    course = resolve_course(course)
    path = Path(assessment_file)
    if not path.is_file():
        typer.echo(f"File not found: {assessment_file}", err=True)
        raise typer.Exit(1)
    try:
        rubric_assessment = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.echo(f"Invalid JSON in {assessment_file}: {exc}", err=True)
        raise typer.Exit(1)

    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)
        data = await submit_rubric_grade(
            ectx.client,
            course_id,
            assignment_id,
            user_id,
            rubric_assessment,
            comment=comment,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, fmt)
