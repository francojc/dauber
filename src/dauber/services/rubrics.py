"""Rubrics service — list, detail, create, and assessment form-data builder."""

from __future__ import annotations

import csv
from typing import Any

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError


async def list_rubrics(
    client: CanvasClient,
    course_id: str,
) -> list[dict[str, Any]]:
    """Fetch all rubrics for a course."""
    try:
        rubrics = await client.get_paginated(
            f"/courses/{course_id}/rubrics",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list rubrics for course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "id": r["id"],
            "title": r.get("title", ""),
            "points_possible": r.get("points_possible", ""),
            "criteria_count": len(r.get("data", [])),
        }
        for r in rubrics
    ]


async def get_rubric(
    client: CanvasClient,
    course_id: str,
    rubric_id: str,
) -> dict[str, Any]:
    """Fetch a single rubric with full criteria detail."""
    try:
        r = await client.request(
            "get",
            f"/courses/{course_id}/rubrics/{rubric_id}",
            params={"include[]": ["assessments"]},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get rubric {rubric_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    criteria = []
    for c in r.get("data", []):
        criteria.append(
            {
                "id": c.get("id", ""),
                "description": c.get("description", ""),
                "points": c.get("points", 0),
                "ratings": [
                    {
                        "id": rt.get("id", ""),
                        "description": rt.get("description", ""),
                        "points": rt.get("points", 0),
                    }
                    for rt in c.get("ratings", [])
                ],
            }
        )

    return {
        "id": r["id"],
        "title": r.get("title", ""),
        "points_possible": r.get("points_possible", ""),
        "criteria": criteria,
    }


async def create_rubric(
    client: CanvasClient,
    course_id: str,
    title: str,
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a new rubric for a course from a list of criteria dicts."""
    if not criteria:
        raise ValueError("criteria must not be empty")
    for i, c in enumerate(criteria):
        for field in ("description", "points", "ratings"):
            if field not in c:
                raise ValueError(f"criteria[{i}] missing required field '{field}'")

    pairs: list[tuple[str, str]] = [("rubric[title]", title)]
    for i, c in enumerate(criteria):
        pairs.append((f"rubric[criteria][{i}][description]", c["description"]))
        pairs.append((f"rubric[criteria][{i}][points]", str(c["points"])))
        for j, rating in enumerate(c["ratings"]):
            pairs.append(
                (
                    f"rubric[criteria][{i}][ratings][{j}][description]",
                    rating["description"],
                )
            )
            pairs.append(
                (
                    f"rubric[criteria][{i}][ratings][{j}][points]",
                    str(rating["points"]),
                )
            )

    try:
        r = await client.request(
            "post",
            f"/courses/{course_id}/rubrics",
            form_data=pairs,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to create rubric: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    rubric = r["rubric"]
    return {
        "id": rubric["id"],
        "title": rubric.get("title", ""),
        "points_possible": rubric.get("points_possible", ""),
        "criteria_count": len(rubric.get("data", [])),
    }


def parse_rubric_csv(path: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse a Canvas wide-format rubric CSV into (title, criteria).

    Canvas CSV format:
        Rubric Name, Criteria Name, Criteria Description, Criteria Enable Range,
        Rating Name, Rating Description, Rating Points,  (repeating triplets)

    Args:
        path: Path to the CSV file.

    Returns:
        Tuple of (rubric_title, criteria_list).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: On empty file, missing columns, or non-numeric points.
    """
    with open(path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty")

    header = rows[0]
    data_rows = [r for r in rows[1:] if any(cell.strip() for cell in r)]

    if not data_rows:
        raise ValueError("CSV file has no data rows")

    required = [
        "Rubric Name",
        "Criteria Name",
        "Criteria Description",
        "Criteria Enable Range",
    ]
    for col in required:
        if col not in header:
            raise ValueError(f"Missing required column: {col}")

    # Fixed columns occupy indices 0-3; rating triplets begin at index 4.
    fixed_count = 4
    num_triplets = (len(header) - fixed_count) // 3

    if num_triplets == 0:
        raise ValueError("No rating columns found in CSV")

    rubric_names = {row[0].strip() for row in data_rows if row and row[0].strip()}
    if not rubric_names:
        raise ValueError("No rubric name found")
    if len(rubric_names) > 1:
        raise ValueError(
            f"Multiple rubric names found: {', '.join(sorted(rubric_names))}"
        )

    title = rubric_names.pop()
    criteria: list[dict[str, Any]] = []

    for row in data_rows:
        padded = row + [""] * (len(header) - len(row))

        ratings: list[dict[str, Any]] = []
        for t in range(num_triplets):
            base = fixed_count + t * 3
            r_name = padded[base].strip() if base < len(padded) else ""
            r_pts_str = padded[base + 2].strip() if base + 2 < len(padded) else ""

            if not r_name and not r_pts_str:
                continue

            if not r_pts_str:
                continue

            try:
                pts = float(r_pts_str)
            except ValueError:
                raise ValueError(
                    f"Non-numeric points '{r_pts_str}' for rating '{r_name}'"
                )

            pts_val: int | float = int(pts) if pts == int(pts) else pts
            r_desc = padded[base + 1].strip() if base + 1 < len(padded) else ""
            ratings.append({"description": r_name or r_desc, "points": pts_val})

        if not ratings:
            crit_name = padded[1].strip() if len(padded) > 1 else ""
            raise ValueError(f"No ratings found for criterion '{crit_name}'")

        max_pts: int | float = max(r["points"] for r in ratings)
        criteria.append(
            {
                "description": padded[1].strip(),
                "points": max_pts,
                "ratings": ratings,
            }
        )

    return title, criteria


async def attach_rubric(
    client: CanvasClient,
    course_id: str,
    rubric_id: str,
    assignment_id: str,
    use_for_grading: bool = False,
) -> dict[str, Any]:
    """Associate an existing rubric with an assignment.

    Args:
        client: Authenticated CanvasClient.
        course_id: Course numeric ID or code.
        rubric_id: Rubric ID to attach.
        assignment_id: Assignment ID to attach the rubric to.
        use_for_grading: Whether the rubric scores map to the assignment grade.

    Returns:
        Summary dict with rubric_id, assignment_id, use_for_grading, purpose.

    Raises:
        CanvasError: On HTTP errors from the Canvas API.
    """
    try:
        await client.request(
            "put",
            f"/courses/{course_id}/rubrics/{rubric_id}",
            data={
                "rubric_association": {
                    "association_id": assignment_id,
                    "association_type": "Assignment",
                    "use_for_grading": use_for_grading,
                    "purpose": "grading",
                }
            },
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to attach rubric {rubric_id} to assignment {assignment_id}:"
            f" {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "rubric_id": rubric_id,
        "assignment_id": assignment_id,
        "use_for_grading": use_for_grading,
        "purpose": "grading",
    }


def build_rubric_assessment_form_data(
    rubric_assessment: dict[str, dict[str, Any]],
    comment: str | None = None,
) -> list[tuple[str, str]]:
    """Build bracket-notation form data for rubric grade submission.

    Canvas expects form-encoded keys like::

        rubric_assessment[_8027][points]=5
        rubric_assessment[_8027][comments]=Good work

    Args:
        rubric_assessment: Mapping of criterion_id to dict with
            ``points`` and optional ``comments``.
        comment: Overall submission comment.

    Returns:
        List of (key, value) tuples suitable for ``form_data``.
    """
    pairs: list[tuple[str, str]] = []

    for criterion_id, assessment in rubric_assessment.items():
        prefix = f"rubric_assessment[{criterion_id}]"
        pairs.append((f"{prefix}[points]", str(assessment["points"])))
        if "comments" in assessment:
            pairs.append((f"{prefix}[comments]", str(assessment["comments"])))
        if "rating_id" in assessment:
            pairs.append((f"{prefix}[rating_id]", str(assessment["rating_id"])))

    if comment is not None:
        pairs.append(("comment[text_comment]", comment))

    return pairs
