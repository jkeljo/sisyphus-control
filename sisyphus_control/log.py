from typing import Dict, Any

import difflib
import logging

_LOGGER = logging.getLogger("sisyphus-control")


def log_data_change(old: Dict[str, Any], new: Dict[str, Any]) -> None:
    if old == None:
        old = {}

    diff_lines = [line for line in difflib.unified_diff(
        sorted(["{key} = {value}".format(key=item[0], value=item[1])
                for item in old.items()]),
        sorted(["{key} = {value}".format(key=item[0], value=item[1])
                for item in new.items()]),
        "Before",
        "After")]

    if diff_lines:
        _LOGGER.debug("State changed: \n" + "\n".join(diff_lines))
