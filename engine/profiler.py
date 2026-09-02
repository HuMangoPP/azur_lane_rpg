from __future__ import annotations

from contextlib import contextmanager
import time


EXECUTION_TIMES: dict[str, list[float]] = {}

@contextmanager
def profile(name: str):
    """Wrap a block of code to measure execution time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    execution_times = EXECUTION_TIMES.setdefault(name, [])
    execution_times.append(elapsed * 1000)


def print_execution_times():
    """Print execution time stats."""
    for name, execution_times in EXECUTION_TIMES.items():
        min_execution_time = min(execution_times)
        average_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        print(f"{name}: {min_execution_time} | {average_execution_time:.2f} | {max_execution_time} ms")
