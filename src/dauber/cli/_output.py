import csv
import json
import sys
from enum import Enum

from rich.console import Console
from rich.table import Table

console = Console()


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    PLAIN = "plain"
    CSV = "csv"


def format_output(
    data: dict | list[dict],
    fmt: OutputFormat,
    headers: list[str] | None = None,
) -> None:
    """Format and print data according to the chosen output format."""
    if fmt == OutputFormat.JSON:
        console.print(json.dumps(data, indent=2, default=str))
        return

    if fmt == OutputFormat.PLAIN:
        if isinstance(data, dict):
            for key, value in data.items():
                console.print(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        console.print(f"{key}: {value}")
                    console.print("---")
                else:
                    console.print(str(item))
        return

    if fmt == OutputFormat.CSV:
        if isinstance(data, dict):
            data = [data]
        if not data:
            return
        cols = headers or list(data[0].keys())
        writer = csv.writer(sys.stdout)
        writer.writerow(cols)
        for row in data:
            writer.writerow([str(row.get(col, "")) for col in cols])
        return

    # TABLE format
    if isinstance(data, dict):
        data = [data]

    if not data:
        console.print("[dim]No data.[/dim]")
        return

    cols = headers or list(data[0].keys())
    table = Table()
    for col in cols:
        table.add_column(col)
    for row in data:
        table.add_row(*(str(row.get(col, "")) for col in cols))
    console.print(table)
