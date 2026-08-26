from pathlib import Path

from tablevalidate.schema import (
    Row,
    TableFragment,
    TableWithFragments,
    TablesFile,
)


def gather_tablesfiles(
    tablesfiles_with_paths: list[tuple[TablesFile, Path]],
    citation_column: str,
    key_columns: list[str],
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

        for table in tablesfile.tables:
            for fragment in table.get_table_fragments():
                for row in fragment.rows:
                    all_rows.append(Row(**{citation_column: citation, **row.get_columns()}))

    if key_columns:
        all_rows.sort(
            key=lambda r: tuple(str(r.get_columns().get(k, "")) for k in key_columns)
        )

    fragment = TableFragment(rows=all_rows, page=1)
    return TablesFile(
        tables=[TableWithFragments(table_fragments=[fragment])],
        citation="",
    )
