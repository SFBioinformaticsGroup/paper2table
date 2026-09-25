import jsonc
from pathlib import Path
from typing import Any


def load_jsonc(path: Path) -> Any:
    return jsonc.loads(path.read_text(encoding="utf-8"))
