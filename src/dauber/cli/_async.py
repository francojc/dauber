import asyncio
from functools import wraps


def async_command(func):
    """Bridge decorator: call an async function from a sync Typer command."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper
