from paper2table.hints import parse_column_hints


def test_simple_newline_separated():
    hints = "id\nname\nfamily"
    assert parse_column_hints(hints) == ["id", "name", "family"]


def test_blank_lines_ignored():
    hints = "id\n\nname\n\n\nfamily\n"
    assert parse_column_hints(hints) == ["id", "name", "family"]


def test_with_diacritics():
    hints = "id\nnombre_científico"
    assert parse_column_hints(hints) == ["id", "nombre_cientifico"]


def test_uppercase_and_mixed_case():
    hints = "ID\nVernacular_Name\nSCIENTIFIC_NAME"
    assert parse_column_hints(hints) == [
        "id",
        "vernacular_name",
        "scientific_name",
    ]


def test_empty_input():
    hints = ""
    assert parse_column_hints(hints) == []
