
def compute_paper_stats(paper_data):
    tables = paper_data.get("tables", [])
    tables_count = len(tables)
    rows_count = sum(len(t.get("rows", [])) for t in tables)
    rows_with_agreement = sum(
        sum(1 for r in t.get("rows", []) if r.get("_agreement_level", 0) > 1)
        for t in tables
    )

    paper_stats = {
        "tables": tables_count,
        "rows": rows_count,
        "rows_with_agreement": rows_with_agreement,
    }

    if rows_count > 0:
        paper_stats["agreement_percentage"] = rows_with_agreement / rows_count * 100

    return paper_stats
