import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .schema import TablesFile


def validate_file(path: Path) -> Optional[ValueError]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        TablesFile.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        return e
