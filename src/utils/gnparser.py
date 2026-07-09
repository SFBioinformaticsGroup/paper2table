import json
import subprocess


def parse_scientific_name(name: str) -> str:
    try:
        result = subprocess.run(
            ["gnparser", "-f", "compact", name],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "gnparser is not installed. "
            "Install it with:\n"
            "  go install github.com/gnames/gnparser/gnparser@latest\n"
            "or download a binary from https://github.com/gnames/gnparser/releases"
        )
    records = json.loads(result.stdout)
    record = records[0] if isinstance(records, list) else records
    normalized = record.get("normalized")
    return normalized if normalized else name
