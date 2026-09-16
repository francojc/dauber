#!/usr/bin/env python3
"""Probe the Canvas Classic Quiz report API (v0.1.14 Phase A).

Read-only by default. With --create it POSTs one report generation for a
single quiz (Canvas creates a report object -- harmless, but it is a write).

Captures the fields that drive the service design:
  - quiz object: id, assignment_id, title, quiz_type, published
  - report object: id, report_type, progress/workflow_state, attachment URL

Usage:
    CANVAS_API_KEY=... CANVAS_BASE_URL=... uv run python scripts/probe_quiz_reports.py --course 74806
    uv run python scripts/probe_quiz_reports.py --course 74806 --assignment 614873 --create
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx


def _client() -> httpx.AsyncClient:
    token = os.environ.get("CANVAS_API_KEY")
    base = os.environ.get("CANVAS_BASE_URL")
    if not token or not base:
        sys.exit("CANVAS_API_KEY and CANVAS_BASE_URL must be set")
    return httpx.AsyncClient(
        base_url=f"{base.rstrip('/')}/api/v1",
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(30.0),
    )


async def _paginated(client: httpx.AsyncClient, endpoint: str) -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        resp = await client.get(endpoint, params={"per_page": 100, "page": page})
        resp.raise_for_status()
        batch = resp.json()
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", required=True)
    parser.add_argument("--assignment", help="filter/resolve by assignment id")
    parser.add_argument("--quiz", help="quiz id for --create (else resolved)")
    parser.add_argument(
        "--create", action="store_true", help="POST one student_analysis report"
    )
    parser.add_argument(
        "--type", default="student_analysis", help="report_type for --create"
    )
    args = parser.parse_args()

    async with _client() as client:
        quizzes = await _paginated(client, f"/courses/{args.course}/quizzes")
        print(f"quizzes: {len(quizzes)}")
        for q in quizzes[:5]:
            print(
                json.dumps(
                    {
                        "id": q.get("id"),
                        "assignment_id": q.get("assignment_id"),
                        "title": q.get("title"),
                        "quiz_type": q.get("quiz_type"),
                        "published": q.get("published"),
                        "keys": sorted(q.keys()),
                    },
                    ensure_ascii=False,
                )
            )
        if quizzes:
            print("full first quiz object:")
            print(json.dumps(quizzes[0], indent=2, ensure_ascii=False))

        quiz_id = args.quiz
        if args.assignment:
            match = [q for q in quizzes if str(q.get("assignment_id")) == args.assignment]
            print(f"assignment {args.assignment} -> {len(match)} quiz match(es)")
            if match:
                quiz_id = str(match[0]["id"])

        if not args.create:
            return 0
        if not quiz_id:
            sys.exit("no quiz id: pass --quiz or a resolvable --assignment")

        resp = await client.post(
            f"/courses/{args.course}/quizzes/{quiz_id}/reports",
            data={"quiz_report[report_type]": args.type},
        )
        print(f"POST reports -> {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

        report = resp.json()
        report_id = report.get("id") or (report.get("quiz_report") or {}).get("id")
        if report_id:
            got = await client.get(
                f"/courses/{args.course}/quizzes/{quiz_id}/reports/{report_id}"
            )
            print(f"GET report {report_id} -> {got.status_code}")
            print(json.dumps(got.json(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
