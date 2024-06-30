from package_utils.context import Context

from package_utils.models import Config, Options, Secrets

context = Context(Options, Config, Secrets)
