"""Classic Quiz service — discovery and Canvas quiz-report lifecycle.

Canvas quiz reports generate asynchronously: `POST .../reports` is
get-or-create, completion is signalled by a `file` key on the report, and
failure (with its message) is only visible through `progress_url`.

Verified against Canvas on 2026-09-16 (see
``specs/dauber-quiz-report-export-spec.md``).
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError

REPORT_TYPES = ("student_analysis", "item_analysis")

QUIZ_LIST_HEADERS = ["id", "assignment_id", "title", "quiz_type", "published", "due_at"]

_SURVEY_TYPES = {"survey", "graded_survey"}

_HTTP_MESSAGES = {
    401: "authentication failed (check CANVAS_API_KEY)",
    403: "not authorized — quiz reports require instructor-level access",
    404: "not found — check the course, quiz, and report identifiers",
}

ProgressCallback = Callable[[str, dict[str, Any]], None]


def _project_quiz(quiz: dict[str, Any]) -> dict[str, Any]:
    """Reduce a Canvas quiz object to the fields dauber reports."""
    return {key: quiz.get(key) for key in QUIZ_LIST_HEADERS}


def _unwrap_report(payload: Any) -> dict[str, Any]:
    """Return the report dict from a Canvas report response."""
    if isinstance(payload, dict):
        if "quiz_report" in payload:
            report = payload["quiz_report"]
            if isinstance(report, dict):
                return report
        return payload
    raise CanvasError("Unexpected quiz report response from Canvas.")


def _canvas_error(exc: httpx.HTTPStatusError, what: str) -> CanvasError:
    """Map an HTTP error to a CanvasError with an actionable message."""
    status = exc.response.status_code
    detail = _HTTP_MESSAGES.get(status, exc.response.text[:200])
    return CanvasError(f"{what}: HTTP {status} ({detail})", status_code=status)


async def list_quizzes(
    client: CanvasClient,
    course_id: str,
    *,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch Classic Quizzes for a course.

    Args:
        client: Canvas API client.
        course_id: Numeric Canvas course ID.
        search: Optional case-insensitive title filter.

    Returns:
        List of projected quiz dicts.

    Raises:
        CanvasError: On HTTP failure.
    """
    params: dict[str, Any] = {}
    if search:
        params["search_term"] = search

    try:
        quizzes = await client.get_paginated(
            f"/courses/{course_id}/quizzes", params=params or None
        )
    except httpx.HTTPStatusError as exc:
        raise _canvas_error(exc, "Could not list quizzes") from exc

    quizzes = [_project_quiz(q) for q in quizzes]
    if search:
        needle = search.lower()
        quizzes = [q for q in quizzes if needle in str(q.get("title") or "").lower()]
    return quizzes


async def get_quiz(
    client: CanvasClient,
    course_id: str,
    quiz_id: str,
) -> dict[str, Any]:
    """Fetch a single Classic Quiz by ID.

    Raises:
        CanvasError: On HTTP failure, with a New Quizzes hint on 404.
    """
    try:
        quiz = await client.request("get", f"/courses/{course_id}/quizzes/{quiz_id}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise CanvasError(
                f"Quiz {quiz_id} not found in course {course_id}. "
                "New Quizzes (Quizzes.Next) have no Classic Quiz report "
                "export and are unsupported.",
                status_code=404,
            ) from exc
        raise _canvas_error(exc, f"Could not fetch quiz {quiz_id}") from exc
    return _project_quiz(quiz)


async def resolve_assignment_to_quiz(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
) -> dict[str, Any]:
    """Find the Classic Quiz backing *assignment_id*.

    Matches on the quiz's `assignment_id`. Assignment IDs and quiz IDs are
    different Canvas identifiers and are never assumed equal.

    Raises:
        CanvasError: When no Classic Quiz matches the assignment.
    """
    quizzes = await list_quizzes(client, course_id)
    for quiz in quizzes:
        if str(quiz.get("assignment_id")) == str(assignment_id):
            return quiz

    raise CanvasError(
        f"No Classic Quiz found for assignment {assignment_id} in course "
        f"{course_id}. If this assignment is a New Quiz (Quizzes.Next), "
        "report export is unsupported."
    )


async def list_reports(
    client: CanvasClient,
    course_id: str,
    quiz_id: str,
) -> list[dict[str, Any]]:
    """List existing quiz-report stubs for a Classic Quiz."""
    try:
        payload = await client.request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}/reports"
        )
    except httpx.HTTPStatusError as exc:
        raise _canvas_error(exc, f"Could not list reports for quiz {quiz_id}") from exc

    if isinstance(payload, dict):
        reports = payload.get("quiz_reports", [])
    else:
        reports = payload
    return [r for r in reports if isinstance(r, dict)]


async def create_report(
    client: CanvasClient,
    course_id: str,
    quiz_id: str,
    *,
    report_type: str = "student_analysis",
    includes_all_versions: bool = False,
) -> dict[str, Any]:
    """Request (or re-request) a quiz report.

    Canvas treats this as get-or-create: the same report ID is returned when
    a report exists for the (`report_type`, `includes_all_versions`) pair.

    Raises:
        CanvasError: On HTTP failure or unsupported report type.
    """
    if report_type not in REPORT_TYPES:
        raise CanvasError(
            f"Unsupported report type '{report_type}'. "
            f"Expected one of: {', '.join(REPORT_TYPES)}."
        )

    form_data = [
        ("quiz_report[report_type]", report_type),
        (
            "quiz_report[includes_all_versions]",
            "true" if includes_all_versions else "false",
        ),
    ]
    try:
        payload = await client.request(
            "post",
            f"/courses/{course_id}/quizzes/{quiz_id}/reports",
            form_data=form_data,
        )
    except httpx.HTTPStatusError as exc:
        raise _canvas_error(exc, f"Could not create {report_type} report") from exc
    return _unwrap_report(payload)


async def get_report(
    client: CanvasClient,
    course_id: str,
    quiz_id: str,
    report_id: str,
) -> dict[str, Any]:
    """Fetch a single quiz report by ID."""
    try:
        payload = await client.request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}/reports/{report_id}"
        )
    except httpx.HTTPStatusError as exc:
        raise _canvas_error(exc, f"Could not fetch report {report_id}") from exc
    return _unwrap_report(payload)


async def _fetch_progress(client: CanvasClient, progress_url: str) -> tuple[str, str]:
    """Return (workflow_state, message) from a Canvas progress URL."""
    endpoint = progress_url.split("/api/v1", 1)[-1] if "/api/v1" in progress_url else ""
    if not endpoint:
        return "", ""
    try:
        progress = await client.request("get", endpoint)
    except httpx.HTTPStatusError:
        return "", ""
    if not isinstance(progress, dict):
        return "", ""
    return str(progress.get("workflow_state") or ""), str(progress.get("message") or "")


async def wait_for_report(
    client: CanvasClient,
    course_id: str,
    quiz_id: str,
    report_id: str,
    *,
    progress_url: str | None = None,
    timeout: float = 300.0,
    initial_interval: float = 1.0,
    max_interval: float = 10.0,
    on_progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Poll a quiz report until it completes, fails, or times out.

    Completion is signalled by a `file` key on the report; failure (and its
    Canvas message) is only visible via the progress endpoint, so both are
    polled.

    Raises:
        CanvasError: On Canvas-reported failure or timeout.
    """
    interval = initial_interval
    elapsed = 0.0
    last_state = "queued"

    while True:
        report = await get_report(client, course_id, quiz_id, report_id)
        if report.get("file"):
            if on_progress:
                on_progress("completed", report)
            return report

        if progress_url:
            state, message = await _fetch_progress(client, progress_url)
            if state:
                last_state = state
            if state == "failed":
                raise CanvasError(
                    f"Report {report_id} generation failed: "
                    f"{message or 'no message from Canvas'}"
                )
            if on_progress:
                on_progress(state or "queued", report)

        if elapsed >= timeout:
            raise CanvasError(
                f"Timed out after {timeout:.0f}s waiting for report "
                f"{report_id} (last state: {last_state})."
            )

        await asyncio.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, max_interval)


def report_file(report: dict[str, Any]) -> dict[str, Any] | None:
    """Return the report's attachment dict, if present."""
    file = report.get("file")
    return file if isinstance(file, dict) else None


async def download_report(client: CanvasClient, report: dict[str, Any]) -> bytes:
    """Download a completed report attachment and return its bytes.

    Uses the URL returned by Canvas; URLs are never constructed.

    Raises:
        CanvasError: When the report has no attachment or the download fails.
    """
    file = report_file(report)
    if not file or not file.get("url"):
        raise CanvasError(
            f"Report {report.get('id')} has no attachment yet; "
            "it is still generating or has expired."
        )
    try:
        return await client.download(str(file["url"]))
    except httpx.HTTPStatusError as exc:
        raise _canvas_error(
            exc, f"Could not download report {report.get('id')}"
        ) from exc


def is_survey_quiz(quiz: dict[str, Any] | None) -> bool:
    """Whether *quiz* is a survey-type quiz (affects report naming)."""
    return str((quiz or {}).get("quiz_type") or "") in _SURVEY_TYPES
