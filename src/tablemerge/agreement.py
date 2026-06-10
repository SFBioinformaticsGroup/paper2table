from typing import Protocol

from tablevalidate.schema import Row


class Agreement(Protocol):
    def calculate_level(self, left: Row, right: Row) -> int: ...


def is_agent_reader(reader: str | None) -> bool:
    if not reader:
        return True
    if reader in ("pdfplumber", "camelot", "pymupdf"):
        return False
    if reader.startswith("hybrid-"):
        return False
    return True


class SimpleCountAgreement:
    def calculate_level(self, left: Row, right: Row) -> int:
        return left.get_agreement_level() + right.get_agreement_level()


class DistinctReadersAgreement:
    def __init__(self, uuid_to_reader: dict[str, str]):
        self.uuid_to_reader = uuid_to_reader

    def calculate_level(self, left: Row, right: Row) -> int:
        sources = list(dict.fromkeys((left.sources_ or []) + (right.sources_ or [])))
        agent_count = 0
        non_agent_readers: set[str] = set()
        for uuid in sources:
            reader = self.uuid_to_reader.get(uuid)
            if is_agent_reader(reader):
                agent_count += 1
            elif reader is not None:
                non_agent_readers.add(reader)
        return max(1, agent_count + len(non_agent_readers))
