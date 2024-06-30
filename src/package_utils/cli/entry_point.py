from package_utils import main
from package_utils.context import context
from package_utils.context.entry_point import create_entry_point

entry_point = create_entry_point(main, context)
