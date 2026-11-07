import re

COLUMN_DELIMITER = re.compile(r"\s+|,\s*(?=[a-zA-Z_]\w*:)")

def tokenize_schema(text: str) -> list[str]:
    """extract column definitions"""
    stripped = " ".join(line.partition("#")[0] for line in text.splitlines())
    return [part.strip() for part in COLUMN_DELIMITER.split(stripped) if part.strip()]
