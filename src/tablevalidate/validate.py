import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .schema import TablesFile


class MalformedJsonError(ValueError):
    def __init__(self, cause: json.JSONDecodeError):
        super().__init__(str(cause))
        self.cause = cause


def validate_file(path: Path) -> Optional[ValueError]:
    try:
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                return MalformedJsonError(e)
    except FileNotFoundError:
        return FileNotFoundError(f"No such file: {path}")
    try:
        TablesFile.model_validate(data)
        return None
    except ValidationError as e:
        return e
