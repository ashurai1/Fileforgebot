"""
ConvertX Bot - Async Job Queue Manager
Manages conversion jobs with an asyncio queue and a configurable worker pool.
Supports per-user cancellation.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from bot.config import MAX_WORKERS, logger


@dataclass
class Job:
    """Represents a single conversion job."""
    user_id: int
    coro: Coroutine
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


class QueueManager:
    """Async job queue with worker pool and cancellation support."""

    def __init__(self, max_workers: int = MAX_WORKERS) -> None:
        self.max_workers = max_workers
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._cancel_tokens: dict[int, bool] = {}  # user_id -> cancelled
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start the worker pool."""
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(task)
        logger.info("Queue manager started with %d workers", self.max_workers)

    async def stop(self) -> None:
        """Gracefully stop all workers."""
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Queue manager stopped")

    async def _worker(self, name: str) -> None:
        """Worker loop that processes jobs from the queue."""
        while True:
            job = await self._queue.get()
            try:
                if self._cancel_tokens.get(job.user_id, False):
                    job.future.set_result(None)
                    logger.info("%s: Job for user %s was cancelled", name, job.user_id)
                    continue
                result = await job.coro
                if not job.future.done():
                    job.future.set_result(result)
            except Exception as exc:
                if not job.future.done():
                    job.future.set_exception(exc)
                logger.error("%s: Job failed for user %s: %s", name, job.user_id, exc)
            finally:
                self._queue.task_done()

    async def submit(self, user_id: int, coro: Coroutine) -> asyncio.Future:
        """Submit a job and return a future for the result."""
        self._cancel_tokens.pop(user_id, None)  # reset cancel flag
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        job = Job(user_id=user_id, coro=coro, future=future)
        await self._queue.put(job)
        logger.debug("Job queued for user %s (queue size: %d)", user_id, self._queue.qsize())
        return future

    def cancel(self, user_id: int) -> None:
        """Request cancellation for the given user's pending jobs."""
        self._cancel_tokens[user_id] = True
        logger.info("Cancellation requested for user %s", user_id)

    def is_cancelled(self, user_id: int) -> bool:
        """Check if a user's job has been cancelled."""
        return self._cancel_tokens.get(user_id, False)


# Singleton
queue_manager = QueueManager()
