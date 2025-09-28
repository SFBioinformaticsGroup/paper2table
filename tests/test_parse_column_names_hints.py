from paper2table.readers.pdfplumber import parse_column_names_hints


def test_simple_comma_separated():
    hints = "id, name, family"
    assert parse_column_names_hints(hints) == ["id", "name", "family"]


def test_newline_and_whitespace():
    hints = "id \n name   family"
    assert parse_column_names_hints(hints) == ["id", "name", "family"]


def test_extra_commas_and_spaces():
    hints = "id, ,  ,   name , family"
    assert parse_column_names_hints(hints) == ["id", "name", "family"]


def test_with_diacritics():
    hints = "id, nombre_científico"
    assert parse_column_names_hints(hints) == ["id", "nombre_cientifico"]


def test_uppercase_and_mixed_case():
    hints = "ID, Vernacular_Name, SCIENTIFIC_NAME"
    assert parse_column_names_hints(hints) == [
        "id",
        "vernacular_name",
        "scientific_name",
    ]


def test_empty_input():
    hints = ""
    assert parse_column_names_hints(hints) == []
