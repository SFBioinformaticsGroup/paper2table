from unidecode import unidecode

from .str import normalize_str

import string
from typing import overload


@overload
def normalize_column_name(name: str) -> str: ...
@overload
def normalize_column_name(name: None) -> None: ...
@overload
def normalize_column_name(name: str | None) -> str | None: ...


def normalize_column_name(name: str | None) -> str | None:
    if name is None:
        return None

    name = unidecode(normalize_str(name))
    valid = string.ascii_lowercase + string.digits + "_"
    name = "".join(ch if ch in valid else "_" for ch in name)
    while "__" in name:
        name = name.replace("__", "_")
    return name.strip("_")
