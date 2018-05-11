from typing import Dict, Any

import difflib
import logging

logger = logging.getLogger("sisyphus-control")

def log_data_change(old: Dict[str, any], new: Dict[str, any]) -> None:
    if old == None:
        old = {}

    diff_lines = [line for line in difflib.unified_diff(
        sorted(["{key} = {value}".format(key=item[0], value=item[1]) for item in old.items()]),
        sorted(["{key} = {value}".format(key=item[0], value=item[1]) for item in new.items()]),
        "Before",
        "After")]

    if diff_lines:
        logger.debug("State changed: \n" + "\n".join(diff_lines))