from dataclasses import dataclass

from utils.tokenize_schema import tokenize_schema


@dataclass
class PaperAlias:
    canonical: str
    offset: int = 0


def parse_column_aliases(text: str) -> dict[str, str]:
    aliases = {}
    for part in tokenize_schema(text):
        if ":" in part:
            alias, target = part.split(":", 1)
            aliases[alias] = target
    return aliases


def parse_paper_aliases(text: str) -> dict[str, PaperAlias]:
    aliases = {}
    for part in tokenize_schema(text):
        parts = part.split(":", 2)
        if len(parts) >= 2:
            alias, canonical = parts[0], parts[1]
            if len(parts) == 3:
                try:
                    offset = int(parts[2])
                except ValueError:
                    raise ValueError(
                        f"Invalid page offset in alias '{part}': '{parts[2]}' is not an integer"
                    )
            else:
                offset = 0
            aliases[alias] = PaperAlias(canonical=canonical, offset=offset)
    return aliases
