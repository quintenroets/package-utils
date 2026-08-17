import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent.parent


def run_isolated(source: str) -> None:
    """
    Run source in a fresh interpreter, the only place absent imports are observable.

    Any test in this process has already put the modules under test in `sys.modules`.
    """
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(root / "src"), str(root))),
    }
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", source],
        check=True,
        env=environment,
        cwd=root,
    )
