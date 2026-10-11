import asyncio

_tasks: set[asyncio.Task] = set()


def spawn(coro) -> None:
    """Fire-and-forget. We keep a reference so the task isn't garbage-collected."""
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)