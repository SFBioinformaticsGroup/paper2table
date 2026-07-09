import json
import subprocess


def parse_scientific_name(name: str) -> str:
    try:
        result = subprocess.run(
            ["gnparser", "-f", "compact", "--capitalize", name],
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
    record = json.loads(result.stdout)
    # using canonical form in order to
    # remove author, if possible
    canonical = record.get("canonical", {}).get("full")
    normalized = record.get("normalized")
    return canonical or normalized or name
