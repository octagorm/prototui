"""
Async utilities for TUI workflows.
"""

import asyncio
from typing import Any, Callable, Optional, TypeVar, Awaitable


T = TypeVar("T")


async def run_with_timeout(
    operation: Callable[[], Awaitable[T]],
    timeout: float,
    timeout_value: Optional[T] = None,
) -> T:
    """
    Run an async operation with a timeout.

    Args:
        operation: Async operation to run
        timeout: Timeout in seconds
        timeout_value: Value to return on timeout

    Returns:
        Operation result or timeout_value

    Raises:
        asyncio.TimeoutError: If timeout occurs and timeout_value is None
    """
    try:
        return await asyncio.wait_for(operation(), timeout=timeout)
    except asyncio.TimeoutError:
        if timeout_value is not None:
            return timeout_value
        raise


async def poll_until(
    check_fn: Callable[[], Awaitable[bool]],
    interval: float = 1.0,
    timeout: Optional[float] = None,
    on_check: Optional[Callable[[int], None]] = None,
) -> bool:
    """
    Poll a condition until it becomes true or timeout.

    Args:
        check_fn: Async function that returns True when condition is met
        interval: Polling interval in seconds
        timeout: Maximum time to wait, None for no timeout
        on_check: Optional callback called after each check with attempt number

    Returns:
        True if condition was met, False if timeout

    Example:
        ```python
        # Wait for PR approval
        async def check_pr_status():
            status = await get_pr_status(pr_id)
            return status == "approved"

        approved = await poll_until(
            check_pr_status,
            interval=5.0,
            timeout=300.0,  # 5 minutes
            on_check=lambda n: print(f"Check #{n}...")
        )
        ```
    """
    start_time = asyncio.get_event_loop().time()
    attempt = 0

    while True:
        attempt += 1

        if on_check:
            on_check(attempt)

        if await check_fn():
            return True

        if timeout:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                return False

        await asyncio.sleep(interval)


async def run_parallel(
    *operations: Callable[[], Awaitable[Any]],
) -> list[Any]:
    """
    Run multiple async operations in parallel.

    Args:
        *operations: Async operations to run

    Returns:
        List of results in same order as operations

    Example:
        ```python
        results = await run_parallel(
            lambda: fetch_repos(),
            lambda: fetch_prs(),
            lambda: fetch_builds(),
        )
        repos, prs, builds = results
        ```
    """
    tasks = [op() for op in operations]
    return await asyncio.gather(*tasks)


async def run_parallel_with_limit(
    operations: list[Callable[[], Awaitable[T]]],
    limit: int = 5,
    on_complete: Optional[Callable[[int, T], None]] = None,
) -> list[T]:
    """
    Run multiple async operations in parallel with concurrency limit.

    Args:
        operations: List of async operations
        limit: Maximum concurrent operations
        on_complete: Optional callback when each operation completes

    Returns:
        List of results in same order as operations

    Example:
        ```python
        # Process 100 repos with max 10 concurrent
        ops = [lambda r=repo: process_repo(r) for repo in repos]
        results = await run_parallel_with_limit(
            ops,
            limit=10,
            on_complete=lambda i, r: print(f"Completed {i+1}/{len(ops)}")
        )
        ```
    """
    semaphore = asyncio.Semaphore(limit)
    results = [None] * len(operations)

    async def run_with_semaphore(index: int, op: Callable[[], Awaitable[T]]) -> None:
        async with semaphore:
            result = await op()
            results[index] = result
            if on_complete:
                on_complete(index, result)

    tasks = [run_with_semaphore(i, op) for i, op in enumerate(operations)]
    await asyncio.gather(*tasks)

    return results


async def retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """
    Retry an async operation with exponential backoff.

    Args:
        operation: Async operation to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        on_retry: Optional callback when retrying

    Returns:
        Operation result

    Raises:
        Exception: Last exception if all retries fail

    Example:
        ```python
        result = await retry_with_backoff(
            lambda: unstable_api_call(),
            max_retries=5,
            on_retry=lambda attempt, ex: print(f"Retry {attempt}: {ex}")
        )
        ```
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries:
                raise

            if on_retry:
                on_retry(attempt + 1, e)

            await asyncio.sleep(delay)
            delay *= backoff_factor


class AsyncQueue:
    """
    Simple async queue for workflow communication.

    Example:
        ```python
        queue = AsyncQueue()

        # Producer
        async def producer():
            for i in range(10):
                await queue.put(i)
            await queue.put(None)  # Sentinel

        # Consumer
        async def consumer():
            while True:
                item = await queue.get()
                if item is None:
                    break
                process(item)
        ```
    """

    def __init__(self) -> None:
        """Initialize the queue."""
        self._queue: asyncio.Queue = asyncio.Queue()

    async def put(self, item: Any) -> None:
        """Add an item to the queue."""
        await self._queue.put(item)

    async def get(self) -> Any:
        """Get an item from the queue (waits if empty)."""
        return await self._queue.get()

    def put_nowait(self, item: Any) -> None:
        """Add an item to the queue without waiting."""
        self._queue.put_nowait(item)

    def get_nowait(self) -> Any:
        """Get an item from the queue without waiting."""
        return self._queue.get_nowait()

    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get the queue size."""
        return self._queue.qsize()
