import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from queue import Queue
from typing import TypeVar

T = TypeVar("T")


def run_jobs(
    jobs: Iterable[Callable[..., T]],
    number_of_workers: int = 0,
    *,
    use_multiprocessing: bool = False,
) -> Iterator[T]:
    if number_of_workers <= 0:
        return (job() for job in jobs)
    executor_class = ProcessPoolExecutor if use_multiprocessing else ThreadPoolExecutor
    executor = executor_class(max_workers=number_of_workers)
    results: Queue[Future[T] | None] = Queue(maxsize=number_of_workers * 2)

    def launch_jobs() -> None:
        with executor:
            for job in jobs:
                future = executor.submit(job)
                future.add_done_callback(results.put)
        results.put(None)

    threading.Thread(target=launch_jobs).start()
    return extract_results(results)


def extract_results(futures: Queue[Future[T] | None]) -> Iterator[T]:
    future = futures.get()
    while future is not None:
        yield future.result()
        future = futures.get()
