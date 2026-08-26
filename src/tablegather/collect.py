from pathlib import Path

from tablevalidate.schema import (
    Row,
    TableFragment,
    TableWithFragments,
    TablesFile,
)
from utils.convergence import convergent_row_ids


def gather_tablesfiles(
    tablesfiles_with_paths: list[tuple[TablesFile, Path]],
    citation_column: str,
    key_columns: list[str],
    path_column: str | None = None,
    only_convergent: bool = False,
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

        source_rows = [
            row
            for table in tablesfile.tables
            for fragment in table.get_table_fragments()
            for row in fragment.rows
        ]

        if only_convergent:
            convergent_ids = convergent_row_ids(source_rows)
            source_rows = [row for row in source_rows if row.row_ in convergent_ids]

        gathered = [Row(**{**extra, **row.get_columns()}) for row in source_rows]
        print(f"{path}: {len(gathered)} rows")
        all_rows.extend(gathered)

    if key_columns:
        all_rows.sort(
            key=lambda r: tuple(str(r.get_columns().get(k, "")) for k in key_columns)
        )

    fragment = TableFragment(rows=all_rows, page=1)
    return TablesFile(
        tables=[TableWithFragments(table_fragments=[fragment])],
        citation="",
    )
