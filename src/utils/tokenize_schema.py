def tokenize_schema(hints: str) -> list[str]:
    return [
        part.strip()
        for part in hints.replace(",", " ").replace("\n", " ").split()
        if part.strip()
    ]
