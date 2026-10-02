import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .schema import TablesFile
from utils.jsonc import load_jsonc


class MalformedJsonError(ValueError):
    def __init__(self, cause: json.JSONDecodeError):
        super().__init__(str(cause))
        self.cause = cause


def validate_file(path: Path) -> Optional[Exception]:
    try:
        try:
            data = load_jsonc(path)
        except json.JSONDecodeError as e:
            return MalformedJsonError(e)
    except FileNotFoundError:
        return FileNotFoundError(f"No such file: {path}")
    try:
        TablesFile.model_validate(data)
        return None
    except ValidationError as e:
        return e
