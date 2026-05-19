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


def test_apply_page_offset():
    table = {
        "table_fragments": [
            {"rows": [{"a": "1"}], "page": 1},
            {"rows": [{"a": "2"}], "page": 2},
        ]
    }
    result = fix_page_numbers(table, 4)
    assert result["table_fragments"][0]["page"] == 5
    assert result["table_fragments"][1]["page"] == 6


def test_apply_page_offset_no_fragments():
    table = {"rows": [{"a": "1"}], "page": 1}
    result = fix_page_numbers(table, 2)
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
    result = read_tables_from_pages("/some/path/doc.pdf", [(0, r1), (1, r2)])
    assert isinstance(result, SplitPagesTablesReader)
    assert len(result.to_dict()["tables"]) == 2
    assert result.to_dict()["tables"][0]["table_fragments"][0]["page"] == 1
    assert result.to_dict()["tables"][1]["table_fragments"][0]["page"] == 2


def test_read_tables_from_pages_takes_first_citation():
    r1 = FakeTablesReader(tables=[], citation=None)
    r2 = FakeTablesReader(tables=[], citation="Author 2026")
    r3 = FakeTablesReader(tables=[], citation="Other 2026")
    result = read_tables_from_pages("/p/doc.pdf", [(0, r1), (1, r2), (2, r3)])
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

    result = read_tables(DEMO_PDF, spy_reader, page_size=1)

    assert len(calls) == 1  # demo_table.pdf has 1 page
    assert calls[0].endswith(".pdf")
    assert isinstance(result, SplitPagesTablesReader)


def test_read_tables_with_page_size_none_sends_all_pages_in_one_call():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    read_tables(DEMO_PDF, spy_reader, page_size=None)
    assert len(calls) == 1  # all pages in one batch


def test_read_tables_with_page_size_1_sends_one_page_per_call():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    read_tables(DEMO_PDF, spy_reader, page_size=1)
    assert len(calls) == 1  # demo_table.pdf has 1 page, so 1 batch of 1


def test_read_tables_page_numbers_correct_with_page_size_1():
    def fake_reader(_page_path):
        return FakeTablesReader(
            tables=[{"table_fragments": [{"rows": [], "page": 1}]}],
            citation=None,
        )

    result = read_tables(DEMO_PDF, fake_reader, page_size=1)
    fragments = result.to_dict()["tables"][0]["table_fragments"]
    assert fragments[0]["page"] == 1  # demo_table.pdf page 1 -> physical page 1


def test_read_tables_corrects_page_numbers():
    def fake_reader(_page_path):
        return FakeTablesReader(
            tables=[{"table_fragments": [{"rows": [], "page": 1}]}],
            citation=None,
        )

    result = read_tables(DEMO_PDF, fake_reader)
    fragments = result.to_dict()["tables"][0]["table_fragments"]
    assert fragments[0]["page"] == 1  # demo_table.pdf page 1 stays 1


def test_read_tables_page_range_includes_matching_page():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    # demo_table.pdf has 1 page; range [1, 3] includes page 1
    read_tables(DEMO_PDF, spy_reader, page_range=(1, 3))
    assert len(calls) == 1


def test_read_tables_page_range_skips_pages_outside_range():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    # demo_table.pdf has 1 page; range [2, 5] excludes page 1
    result = read_tables(DEMO_PDF, spy_reader, page_range=(2, 5))
    assert len(calls) == 0
    assert result.to_dict()["tables"] == []


def test_read_tables_no_page_range_processes_all_pages():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(tables=[], citation=None)

    read_tables(DEMO_PDF, spy_reader, page_range=None)
    assert len(calls) == 1  # demo_table.pdf has 1 page


def test_read_tables_range_without_split_sends_one_batch():
    calls = []

    def spy_reader(page_path):
        calls.append(page_path)
        return FakeTablesReader(
            tables=[{"table_fragments": [{"rows": [], "page": 1}]}],
            citation=None,
        )

    # range specified, page_size=None -> one single call for all pages in range
    result = read_tables(DEMO_PDF, spy_reader, page_range=(1, 1), page_size=None)
    assert len(calls) == 1
    assert result.to_dict()["tables"][0]["table_fragments"][0]["page"] == 1
