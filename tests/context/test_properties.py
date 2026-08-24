from unittest.mock import patch

from package_dev_utils.tests.args import no_cli_args

from package_utils.context import Context as Context_
from tests.context.models.models import Config, Options, Secrets

Context = Context_[Options, Config, Secrets]


@no_cli_args
def test_load_called_at_most_once() -> None:
    context = Context(Options, Config, Secrets)
    with patch.object(context.loaders.options, "load") as mocked_load:
        for _ in range(2):
            _ = context.options
        mocked_load.assert_called_once()
