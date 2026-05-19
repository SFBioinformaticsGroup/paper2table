import re
from typing import Optional, Tuple


def parse_page_range(path: str) -> Tuple[str, Optional[Tuple[int, int]]]:
    """Parse a path that may include a page range suffix in the form PATH:FROM:TO.

    Page numbers are 1-indexed and inclusive. Returns (clean_path, None) when no
    range is present.
    """
    match = re.match(r"^(.+):(\d+):(\d+)$", path)
    if match:
        return match.group(1), (int(match.group(2)), int(match.group(3)))
    return path, None
