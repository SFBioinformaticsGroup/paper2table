from pathlib import Path
from typing import Optional


def read_path(path: Optional[str], inline: Optional[str]) -> Optional[str]:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if inline:
        return inline
    return None
