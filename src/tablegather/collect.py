from pathlib import Path
from typing import Literal

from tablevalidate.schema import (
    Row,
    TableFragment,
    TableWithFragments,
    TablesFile,
)

Convergence = Literal["none", "rows", "fragments", "tables"]


def apply_tables_convergence(tablesfile: TablesFile) -> list[Row]:
    return [
        row
        for table in tablesfile.get_convergent_tables()
        for fragment in table.get_table_fragments()
        for row in fragment.rows
    ]


def apply_fragments_convergence(tablesfile: TablesFile) -> list[Row]:
    return [
        row
        for table in tablesfile.tables
        for fragment in table.get_convergent_fragments()
        for row in fragment.rows
    ]


def apply_rows_convergence(tablesfile: TablesFile) -> list[Row]:
    return [
        row
        for table in tablesfile.tables
        for fragment in table.get_table_fragments()
        for row in fragment.get_convergent_rows()
    ]


def gather_tablesfiles(
    tablesfiles_with_paths: list[tuple[TablesFile, Path]],
    citation_column: str,
    key_columns: list[str],
    path_column: str | None = None,
    convergence: Convergence = "none",
) -> TablesFile:
    seen_citations: set[str] = set()
    all_rows: list[Row] = []

    for tablesfile, path in tablesfiles_with_paths:
        citation = tablesfile.citation
        if not citation or isinstance(citation, list):
            citation = Path(path.stem).stem

        if citation in seen_citations:
            continue
        seen_citations.add(citation)

        extra: dict = {citation_column: citation}
        if path_column:
            extra[path_column] = str(path)

        if convergence == "tables":
            source_rows = apply_tables_convergence(tablesfile)
        elif convergence == "fragments":
            source_rows = apply_fragments_convergence(tablesfile)
        elif convergence == "rows":
            source_rows = apply_rows_convergence(tablesfile)
        else:
            source_rows = [
                row
                for table in tablesfile.tables
                for fragment in table.get_table_fragments()
                for row in fragment.rows
            ]

        gathered = [Row(**{**extra, **row.get_columns()}) for row in source_rows]
        all_rows.extend(gathered)
        if gathered:
            print(f"{path}: {len(gathered)} rows")

    if key_columns:
        all_rows.sort(
            key=lambda r: tuple(str(r.get_columns().get(k, "")) for k in key_columns)
        )

    fragment = TableFragment(rows=all_rows, page=1)
    return TablesFile(
        tables=[TableWithFragments(table_fragments=[fragment])],
        citation="",
    )
