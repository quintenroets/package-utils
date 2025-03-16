from collections.abc import Callable

from package_utils.jobs import run_jobs


def test_run_jobs() -> None:
    def create_job(value: int) -> Callable[[], int]:
        return lambda: 2 * value

    jobs = [create_job(i) for i in range(10)]
    results = list(run_jobs(jobs, number_of_workers=0))
    sequential_results = list(run_jobs(jobs, number_of_workers=1))
    assert results == sequential_results
