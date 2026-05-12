from paper2table.readers.split_pages import (
    SplitPagesTablesReader,
    fix_page_numbers,
    read_tables_from_pages,
    read_tables,
)

DEMO_PDF = "./tests/data/demo_table.pdf"


class FakeTablesReader:
    def __init__(self, tables, citation=None):
        self._tables = tables
        self.citation = citation

    def to_dict(self):
        return {"tables": self._tables, "citation": self.citation}


def test_correct_page_numbers():
    table = {
        "table_fragments": [
            {"rows": [{"a": "1"}], "page": 1},
            {"rows": [{"a": "2"}], "page": 1},
        ]
    }
    result = fix_page_numbers(table, 5)
    assert result["table_fragments"][0]["page"] == 5
    assert result["table_fragments"][1]["page"] == 5


def test_correct_page_numbers_no_fragments():
    table = {"rows": [{"a": "1"}], "page": 1}
    result = fix_page_numbers(table, 3)
    assert result == table


def test_read_tables_from_pages_combines_tables():
    r1 = FakeTablesReader(
        tables=[{"table_fragments": [{"rows": [{"a": "x"}], "page": 1}]}],
        citation=None,
    )
    r2 = FakeTablesReader(
        tables=[{"table_fragments": [{"rows": [{"a": "y"}], "page": 1}]}],
        citation=None,
    )
    result = read_tables_from_pages("/some/path/doc.pdf", [(1, r1), (2, r2)])
    assert isinstance(result, SplitPagesTablesReader)
    assert len(result.to_dict()["tables"]) == 2
    assert result.to_dict()["tables"][0]["table_fragments"][0]["page"] == 1
    assert result.to_dict()["tables"][1]["table_fragments"][0]["page"] == 2


def test_read_tables_from_pages_takes_first_citation():
    r1 = FakeTablesReader(tables=[], citation=None)
    r2 = FakeTablesReader(tables=[], citation="Author 2026")
    r3 = FakeTablesReader(tables=[], citation="Other 2026")
    result = read_tables_from_pages("/p/doc.pdf", [(1, r1), (2, r2), (3, r3)])
    assert result.citation == "Author 2026"


def test_read_tables_from_pages_filename():
    result = read_tables_from_pages("/some/path/my_paper.pdf", [])
    assert result.to_dict()["metadata"]["filename"] == "my_paper.pdf"


def test_read_tables_from_pages_empty():
    result = read_tables_from_pages("/p/doc.pdf", [])
    d = result.to_dict()
    assert d["tables"] == []
    assert d["citation"] is None


def test_read_tables_calls_reader_per_page():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    result = read_tables(DEMO_PDF, spy_reader)

    assert len(calls) == 1  # demo_table.pdf has 1 page
    assert calls[0].endswith(".pdf")
    assert isinstance(result, SplitPagesTablesReader)


def test_read_tables_corrects_page_numbers():
    def fake_reader(_page_path):
        return FakeTablesReader(
            tables=[{"table_fragments": [{"rows": [], "page": 1}]}],
            citation=None,
        )

    result = read_tables(DEMO_PDF, fake_reader)
    fragments = result.to_dict()["tables"][0]["table_fragments"]
    assert fragments[0]["page"] == 1  # demo_table.pdf page 1 stays 1
