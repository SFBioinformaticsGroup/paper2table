import random
from collections import Counter

from tablevalidate.schema import TablesFile
from utils import colval
from utils.column_schema import ColumnSchema


def collect_column_values(
    papers: dict[str, TablesFile], schema: ColumnSchema | None
) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    if schema is not None:
        for column_name in schema.column_names():
            values[column_name] = []

    for tablesfile in papers.values():
        for table in tablesfile.tables:
            for fragment in table.get_table_fragments():
                for row in fragment.rows:
                    columns = (
                        row.get_columns() if schema is not None
                        else row.get_semantic_columns()
                    )
                    for column_name, column_value in columns.items():
                        if schema is not None and column_name not in schema:
                            continue
                        text = colval.to_text(column_value).strip()
                        if not text:
                            continue
                        values.setdefault(column_name, []).append(text)
    return values


def filter_by_length(values: list[str], max_length: int | None) -> list[str]:
    if max_length is None:
        return values
    return [value for value in values if len(value) <= max_length]


def sample_values(
    values: list[str], count: int, max_length: int | None, rng: random.Random
) -> list[str]:
    candidates = list(dict.fromkeys(filter_by_length(values, max_length)))
    if len(candidates) <= count:
        return candidates
    return rng.sample(candidates, count)


def count_values(
    values: list[str], count: int, max_length: int | None
) -> list[tuple[str, int]]:
    candidates = filter_by_length(values, max_length)
    return Counter(candidates).most_common(count)
