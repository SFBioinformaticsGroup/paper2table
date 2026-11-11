def tokenize_schema(text: str) -> list[str]:
    return [
        stripped
        for line in text.splitlines()
        if (stripped := line.partition("#")[0].strip())
    ]
