from typing import Dict, Any

import difflib
import logging

from .data import Model

_LOGGER = logging.getLogger("sisyphus-control")


def log_data_change(old: Model, new: Model) -> None:
    if old == None:
        old = Model({})

    diff_lines = [line for line in difflib.unified_diff(
        sorted(["{key} = {value}".format(key=item[0], value=item[1])
                for item in old.items()]),
        sorted(["{key} = {value}".format(key=item[0], value=item[1])
                for item in new.items()]),
        "Before",
        "After")]

    if diff_lines:
        _LOGGER.debug("State changed: \n" + "\n".join(diff_lines))
