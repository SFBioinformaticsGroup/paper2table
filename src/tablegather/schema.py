

from utils.column_schema import ColumnSchema

## TODO move the key concept to the ColumnSchema instead
# of having this custom helper
def parse_schema_with_keys(text: str) -> tuple[ColumnSchema, list[str]]:
    parts = [p.strip() for p in text.replace(",", " ").replace("\n", " ").split() if p.strip()]
    key_columns = []
    cleaned = []
    for part in parts:
        segments = part.split(":")
        if len(segments) >= 3 and segments[2] == "key":
            key_columns.append(segments[0])
            cleaned.append(f"{segments[0]}:{segments[1]}")
        else:
            cleaned.append(part)
    schema = ColumnSchema.parse(" ".join(cleaned))
    return schema, key_columns
