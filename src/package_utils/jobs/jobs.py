from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from queue import Queue
from typing import TypeVar
from threading import Semaphore, Thread

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
    futures: Queue[Future[T] | None] = Queue()
    submission_semaphore = Semaphore(number_of_workers * 2)
    # large enough to keep all workers busy

    def launch_jobs() -> None:
        with executor:
            for job in jobs:
                submission_semaphore.acquire()
                future = executor.submit(job)
                future.add_done_callback(futures.put)
                future.add_done_callback(lambda _: submission_semaphore.release())
        futures.put(None)

    Thread(target=launch_jobs).start()
    return extract_results(futures)


def extract_results(futures: Queue[Future[T] | None]) -> Iterator[T]:
    future = futures.get()
    while future is not None:
        yield future.result()
        future = futures.get()
