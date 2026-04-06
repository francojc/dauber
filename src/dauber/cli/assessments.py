"""Assessment CLI sub-app — setup, load, update, submit."""

from __future__ import annotations

import json
from typing import Optional

import typer

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_assess_defaults, resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.assessments import (
    build_assessment_structure,
    fetch_assignment_with_rubric,
    fetch_submissions_with_content,
    get_assessment_stats,
    load_assessment,
    save_assessment,
    submit_assessments,
    update_assessment_record,
)

assess_app = typer.Typer(
    name="assess",
    help="Rubric-based assessment workflow (setup, load, update, submit).",
)


@assess_app.command("setup")
@async_command
async def assess_setup(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. Default: .claude/assessments/<auto>.json",
    ),
    course_name: Optional[str] = typer.Option(
        None,
        "--course-name",
        help="Course display name for metadata.",
    ),
    level: Optional[str] = typer.Option(None, "--level", help="Educational level."),
    feedback_language: Optional[str] = typer.Option(
        None, "--feedback-language", help="Feedback language code."
    ),
    language_learning: Optional[bool] = typer.Option(
        None,
        "--language-learning/--no-language-learning",
        help="Language learning course.",
    ),
    language_level: Optional[str] = typer.Option(
        None, "--language-level", help="ACTFL proficiency level."
    ),
    formality: Optional[str] = typer.Option(
        None, "--formality", help="Feedback tone: casual or formal."
    ),
    exclude_graded: bool = typer.Option(
        True,
        "--exclude-graded/--include-graded",
        help="Exclude already-graded submissions.",
    ),
    anonymize: Optional[bool] = typer.Option(
        None,
        "--anonymize/--no-anonymize",
        help="Strip PII (user_name, user_email) for FERPA compliance.",
    ),
) -> None:
    """Fetch assignment data and build an assessment JSON file."""
    course = resolve_course(course)

    # Resolve assess defaults from config (explicit CLI flags win).
    defaults = resolve_assess_defaults(
        {
            "course_name": course_name,
            "level": level,
            "feedback_language": feedback_language,
            "language_learning": language_learning,
            "language_level": language_level,
            "formality": formality,
            "anonymize": anonymize,
        }
    )
    course_name = defaults.get("course_name") or ""
    level = defaults.get("level") or "undergraduate"
    feedback_language = defaults.get("feedback_language") or "en"
    language_learning = defaults.get("language_learning") or False
    language_level = defaults.get("language_level") or "NA"
    formality = defaults.get("formality") or "casual"
    anonymize = defaults.get("anonymize") or False

    ectx = get_context(ctx.obj)
    fmt = ctx.obj["format"]
    try:
        course_id = await ectx.cache.resolve(course)

        assignment_data = await fetch_assignment_with_rubric(
            ectx.client, course_id, assignment_id
        )

        submissions = await fetch_submissions_with_content(
            ectx.client,
            course_id,
            assignment_id,
            exclude_graded=exclude_graded,
            anonymize=anonymize,
        )

        data = build_assessment_structure(
            course_id=course_id,
            course_name=course_name,
            assignment_data=assignment_data,
            submissions=submissions,
            level=level,
            feedback_language=feedback_language,
            language_learning=language_learning,
            language_level=language_level,
            formality=formality,
        )

        if output:
            out_path = output
        else:
            from datetime import datetime, timezone

            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            out_path = f".claude/assessments/{course_id}_{assignment_id}_{ts}.json"

        saved = save_assessment(data, out_path)

    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()

    stats = get_assessment_stats(data)
    summary = {
        "file": str(saved),
        "course_id": course_id,
        "assignment": assignment_data["assignment_name"],
        "points_possible": assignment_data["points_possible"],
        "submissions": stats["total_submissions"],
        "criteria": assignment_data["rubric"]["criteria_count"],
    }
    format_output(summary, fmt)


@assess_app.command("load")
def assess_load(
    ctx: typer.Context,
    file: str = typer.Argument(help="Path to assessment JSON file."),
) -> None:
    """Load an assessment file and display summary statistics."""
    fmt = ctx.obj["format"]
    try:
        data = load_assessment(file)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)

    stats = get_assessment_stats(data)
    meta = data["metadata"]
    summary = {
        "file": file,
        "assignment": meta.get("assignment_name", ""),
        "points_possible": meta.get("points_possible", ""),
        "total_submissions": stats["total_submissions"],
        "reviewed": stats["reviewed"],
        "approved": stats["approved"],
        "not_reviewed": stats["not_reviewed"],
        "score_avg": stats["score_avg"],
        "score_min": stats["score_min"],
        "score_max": stats["score_max"],
    }
    format_output(summary, fmt)


@assess_app.command("update")
def assess_update(
    ctx: typer.Context,
    file: str = typer.Argument(help="Path to assessment JSON file."),
    user_id: str = typer.Argument(help="User ID to update."),
    rubric_json: Optional[str] = typer.Option(
        None,
        "--rubric-json",
        help=(
            "Rubric assessment as JSON string, e.g. "
            '\'{"_c1": {"points": 8, "justification": "Good"}}\'.'
        ),
    ),
    comment: Optional[str] = typer.Option(None, "--comment", help="Overall comment."),
    reviewed: Optional[bool] = typer.Option(
        None, "--reviewed/--not-reviewed", help="Mark as reviewed."
    ),
    approved: Optional[bool] = typer.Option(
        None, "--approved/--not-approved", help="Mark as approved."
    ),
) -> None:
    """Update one student's assessment in a JSON file."""
    fmt = ctx.obj["format"]
    try:
        data = load_assessment(file)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)

    rubric_assessment = None
    if rubric_json:
        try:
            rubric_assessment = json.loads(rubric_json)
        except json.JSONDecodeError as exc:
            typer.echo(f"Invalid JSON: {exc}", err=True)
            raise typer.Exit(1)

    try:
        entry = update_assessment_record(
            data,
            user_id,
            rubric_assessment=rubric_assessment,
            overall_comment=comment,
            reviewed=reviewed,
            approved=approved,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)

    save_assessment(data, file)

    result = {
        "user_id": entry["user_id"],
        "reviewed": entry["reviewed"],
        "approved": entry["approved"],
    }
    format_output(result, fmt)


@assess_app.command("submit")
@async_command
async def assess_submit(
    ctx: typer.Context,
    file: str = typer.Argument(help="Path to assessment JSON file."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment_id: str = typer.Argument(help="Assignment ID."),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Actually submit. Without this flag, shows a dry run.",
    ),
) -> None:
    """Submit approved assessments to Canvas."""
    course = resolve_course(course)
    fmt = ctx.obj["format"]
    try:
        data = load_assessment(file)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)

    stats = get_assessment_stats(data)
    if stats["approved"] == 0:
        typer.echo("No approved assessments to submit.", err=True)
        raise typer.Exit(1)

    if not confirm:
        typer.echo("Dry run — showing what would be submitted.")
        typer.echo(f"Approved: {stats['approved']} / {stats['total_submissions']}")
        typer.echo("Use --confirm to submit to Canvas.")
        raise typer.Exit(0)

    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        result = await submit_assessments(
            ectx.client,
            course_id,
            assignment_id,
            data,
            only_approved=True,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()

    format_output(result, fmt)
