from tablevalidate.schema import Row


def convergent_row_ids(rows: list[Row]) -> frozenset:
    groups: dict = {}
    for row in rows:
        if row.row_ is not None:
            groups.setdefault(row.row_, []).append(row)
    return frozenset(row_id for row_id, group in groups.items() if len(group) == 1)
