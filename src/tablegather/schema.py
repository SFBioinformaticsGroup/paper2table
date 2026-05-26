from utils.columns_schema import parse_schema


def parse_schema_with_keys(text: str) -> tuple[dict, list[str]]:
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
    schema = parse_schema(" ".join(cleaned)) if cleaned else {}
    return schema, key_columns
