import string
import unicodedata
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

    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    valid = string.ascii_lowercase + string.digits + "_"
    name = name.lower()
    name = "".join(ch if ch in valid else "_" for ch in name)
    while "__" in name:
        name = name.replace("__", "_")
    return name.strip("_")
