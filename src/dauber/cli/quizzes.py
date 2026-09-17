"""Quizzes CLI sub-app — Classic Quiz discovery and report export."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console

from dauber.cli._async import async_command
from dauber.cli._config_defaults import resolve_course
from dauber.cli._context import get_context
from dauber.cli._output import format_output
from dauber.services import CanvasError
from dauber.services.quizzes import (
    QUIZ_LIST_HEADERS,
    REPORT_TYPES,
    create_report,
    download_report,
    get_quiz,
    get_report,
    is_survey_quiz,
    list_quizzes,
    list_reports,
    report_file,
    resolve_assignment_to_quiz,
    wait_for_report,
)

quizzes_app = typer.Typer(
    name="quizzes", help="Manage Canvas Classic Quizzes and their reports."
)
reports_app = typer.Typer(name="reports", help="Generate and download quiz reports.")
quizzes_app.add_typer(reports_app)

_console_err = Console(stderr=True)

_REPORT_LABELS = {
    "student_analysis": "Student Analysis Report",
    "item_analysis": "Item Analysis Report",
}

_DEFAULT_TIMEOUT = 300.0


def _validation_error(message: str) -> None:
    """Emit CLI validation errors consistently (exit code 2)."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(2)


def _safe_component(text: str | None) -> str:
    """Make *text* safe for use in a filename."""
    if not text:
        return ""
    cleaned = re.sub(r"[:\\/]+", "_", str(text).strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .")


def derive_report_filename(
    title: str | None,
    report_type: str,
    *,
    survey: bool = False,
    fallback: str | None = None,
) -> str:
    """Build the output filename for a quiz report.

    Derived from the quiz title so names stay stable across runs. Canvas's
    `file.display_name` is only a fallback because it keeps the raw colon and
    stray whitespace from quiz titles.
    """
    label = _REPORT_LABELS.get(report_type, f"{report_type} Report")
    prefix = "Survey " if survey else ""
    name = _safe_component(title)
    if name:
        return f"{name} {prefix}{label}.csv"
    fallback_name = _safe_component(fallback)
    if fallback_name:
        return (
            fallback_name
            if fallback_name.lower().endswith(".csv")
            else f"{fallback_name}.csv"
        )
    return f"quiz_{report_type}_report.csv"


def _resolve_output_path(
    output: Path,
    quiz: dict[str, Any],
    report_type: str,
    report: dict[str, Any],
) -> Path:
    """Resolve the download destination from a user-supplied path."""
    if output.suffix.lower() == ".csv":
        return output
    display_name = (report_file(report) or {}).get("display_name")
    return output / derive_report_filename(
        quiz.get("title"),
        report_type,
        survey=is_survey_quiz(quiz),
        fallback=display_name,
    )


def _write_bytes(path: Path, data: bytes, force: bool) -> Path:
    """Write *data* to *path* atomically, refusing to clobber by default."""
    if path.exists() and not force:
        _validation_error(f"refusing to overwrite {path}; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.part")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def _progress(state: str, report: dict[str, Any]) -> None:
    """Report generation progress to stderr, keeping stdout machine-readable."""
    _console_err.print(f"[dim]report {report.get('id')}: {state}[/dim]")


async def _reuse_report(
    client: Any,
    course_id: str,
    quiz_id: str,
    report_type: str,
    includes_all_versions: bool,
) -> tuple[dict[str, Any] | None, bytes | None]:
    """Return (report, bytes) for a reusable completed report, else (None, None)."""
    for report in await list_reports(client, course_id, quiz_id):
        if report.get("report_type") != report_type:
            continue
        if bool(report.get("includes_all_versions")) != includes_all_versions:
            continue
        if not report_file(report):
            continue
        try:
            return report, await download_report(client, report)
        except CanvasError:
            continue
    return None, None


@quizzes_app.command("list")
@async_command
async def quizzes_list(
    ctx: typer.Context,
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    search: Optional[str] = typer.Option(
        None, "--search", help="Filter quizzes by title."
    ),
) -> None:
    """List Classic Quizzes in a course."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_quizzes(ectx.client, course_id, search=search)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, ctx.obj["format"], headers=list(QUIZ_LIST_HEADERS))


@quizzes_app.command("show")
@async_command
async def quizzes_show(
    ctx: typer.Context,
    quiz_id: str = typer.Argument(..., help="Canvas Classic Quiz ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """Show one Classic Quiz."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_quiz(ectx.client, course_id, quiz_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, ctx.obj["format"], headers=list(QUIZ_LIST_HEADERS))


@quizzes_app.command("resolve-assignment")
@async_command
async def quizzes_resolve_assignment(
    ctx: typer.Context,
    assignment_id: str = typer.Argument(..., help="Canvas assignment ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """Resolve an assignment ID to its Classic Quiz ID."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await resolve_assignment_to_quiz(ectx.client, course_id, assignment_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(data, ctx.obj["format"], headers=list(QUIZ_LIST_HEADERS))


@reports_app.command("list")
@async_command
async def reports_list(
    ctx: typer.Context,
    quiz_id: str = typer.Argument(..., help="Canvas Classic Quiz ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """List existing reports for a quiz."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await list_reports(ectx.client, course_id, quiz_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        ctx.obj["format"],
        headers=["id", "report_type", "includes_all_versions", "updated_at", "url"],
    )


@reports_app.command("create")
@async_command
async def reports_create(
    ctx: typer.Context,
    quiz_id: str = typer.Argument(..., help="Canvas Classic Quiz ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    report_type: str = typer.Option(
        "student_analysis", "--type", help="Report type to generate."
    ),
    all_versions: bool = typer.Option(
        False, "--all-versions", help="Include all submission versions."
    ),
) -> None:
    """Request a quiz report (Canvas reuses an existing report)."""
    course = resolve_course(course)
    if report_type not in REPORT_TYPES:
        _validation_error(
            f"unsupported report type '{report_type}'; "
            f"expected one of: {', '.join(REPORT_TYPES)}"
        )
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await create_report(
            ectx.client,
            course_id,
            quiz_id,
            report_type=report_type,
            includes_all_versions=all_versions,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        ctx.obj["format"],
        headers=["id", "report_type", "includes_all_versions", "url", "progress_url"],
    )


@reports_app.command("show")
@async_command
async def reports_show(
    ctx: typer.Context,
    quiz_id: str = typer.Argument(..., help="Canvas Classic Quiz ID."),
    report_id: str = typer.Argument(..., help="Canvas quiz report ID."),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
) -> None:
    """Show one quiz report."""
    course = resolve_course(course)
    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        data = await get_report(ectx.client, course_id, quiz_id, report_id)
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()
    format_output(
        data,
        ctx.obj["format"],
        headers=[
            "id",
            "report_type",
            "includes_all_versions",
            "updated_at",
            "url",
            "progress_url",
        ],
    )


@reports_app.command("download")
@async_command
async def reports_download(
    ctx: typer.Context,
    quiz_id: Optional[str] = typer.Argument(
        None, help="Canvas Classic Quiz ID (omit when using --assignment)."
    ),
    course: Optional[str] = typer.Option(
        None, "--course", "-c", help="Course code or numeric ID. Falls back to config."
    ),
    assignment: Optional[str] = typer.Option(
        None, "--assignment", help="Resolve the quiz from an assignment ID."
    ),
    report_type: str = typer.Option(
        "student_analysis", "--type", help="Report type to download."
    ),
    all_versions: bool = typer.Option(
        False, "--all-versions", help="Include all submission versions."
    ),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Output directory or exact .csv path."
    ),
    wait: bool = typer.Option(
        True, "--wait/--no-wait", help="Wait for report generation."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing output file."
    ),
    regenerate: bool = typer.Option(
        False, "--regenerate", help="Request a new report instead of reusing one."
    ),
    timeout: float = typer.Option(
        _DEFAULT_TIMEOUT, "--timeout", help="Seconds to wait for generation."
    ),
) -> None:
    """Download a quiz report CSV, generating it when needed."""
    fmt = ctx.obj["format"]
    course = resolve_course(course)
    if quiz_id and assignment:
        _validation_error("pass either a quiz ID or --assignment, not both")
    if not quiz_id and not assignment:
        _validation_error("provide a quiz ID or --assignment")
    if report_type not in REPORT_TYPES:
        _validation_error(
            f"unsupported report type '{report_type}'; "
            f"expected one of: {', '.join(REPORT_TYPES)}"
        )

    ectx = get_context(ctx.obj)
    try:
        course_id = await ectx.cache.resolve(course)
        if assignment:
            quiz = await resolve_assignment_to_quiz(ectx.client, course_id, assignment)
        else:
            quiz = await get_quiz(ectx.client, course_id, str(quiz_id))
        quiz_key = str(quiz.get("id"))

        data: bytes | None = None
        report: dict[str, Any] | None = None
        reused = False
        if not regenerate:
            report, data = await _reuse_report(
                ectx.client, course_id, quiz_key, report_type, all_versions
            )
            reused = report is not None

        if data is None:
            report = await create_report(
                ectx.client,
                course_id,
                quiz_key,
                report_type=report_type,
                includes_all_versions=all_versions,
            )
            if not wait:
                format_output(
                    {
                        "quiz_id": quiz_key,
                        "report_id": report.get("id"),
                        "report_type": report_type,
                        "status": "requested",
                        "url": report.get("url"),
                        "progress_url": report.get("progress_url"),
                    },
                    fmt,
                    headers=[
                        "quiz_id",
                        "report_id",
                        "report_type",
                        "status",
                        "url",
                        "progress_url",
                    ],
                )
                return
            report = await wait_for_report(
                ectx.client,
                course_id,
                quiz_key,
                str(report.get("id")),
                progress_url=report.get("progress_url"),
                timeout=timeout,
                on_progress=_progress,
            )
            data = await download_report(ectx.client, report)

        path = _write_bytes(
            _resolve_output_path(output, quiz, report_type, report or {}),
            data,
            force,
        )
    except CanvasError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(1)
    finally:
        await ectx.close()

    format_output(
        {
            "quiz_id": quiz_key,
            "report_id": (report or {}).get("id"),
            "report_type": report_type,
            "reused": reused,
            "bytes": len(data or b""),
            "path": str(path),
        },
        fmt,
        headers=["quiz_id", "report_id", "report_type", "reused", "bytes", "path"],
    )
