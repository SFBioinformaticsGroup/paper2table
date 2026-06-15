def tokenize_schema(text: str) -> list[str]:
    stripped = " ".join(line.partition("#")[0] for line in text.splitlines())
    return [part.strip() for part in stripped.replace(",", " ").split() if part.strip()]
