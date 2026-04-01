import pytest

from paper2table.mapping import ColumnMapping, TableMapping, TablesMapping
from paper2table.readers.pymupdf import (
    read_tables,
)

def test_read_table_without_options():
    result = read_tables("./tests/data/demo_table.pdf")

    assert result.citation == None
    assert len(result.tables) == 1
    assert result.tables[0].page == 1
    assert result.tables[0].rows == [
        {
            "common_name": "Sunflower",
            "scientific_name": "Helianthus annuus",
            "species": "annuus",
        },
        {
            "common_name": "Rose",
            "scientific_name": "Rosa gallica",
            "species": "gallica",
        },
        {
            "common_name": "Tulip",
            "scientific_name": "Tulipa gesneriana",
            "species": "gesneriana",
        },
        {
            "common_name": "Lavender",
            "scientific_name": "Lavandula angustifolia",
            "species": "angustifolia",
        },
        {
            "common_name": "Oak",
            "scientific_name": "Quercus robur",
            "species": "robur",
        },
        {
            "common_name": "Maple",
            "scientific_name": "Acer saccharum",
            "species": "saccharum",
        },
        {
            "common_name": "Dandelion",
            "scientific_name": "Taraxacum officinale",
            "species": "officinale",
        },
        {
            "common_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
            "species": "vulgaris",
        },
        {
            "common_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia ficus-indica",
            "species": "ficus-indica",
        },
        {
            "common_name": "Coffee",
            "scientific_name": "Coffea arabica",
            "species": "arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_hints():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        column_names_hints="""
    common_names
    especie
    familia
    family
    name
    nombre
    nombre_cientifico
    nombre_comun
    scientific_name
    species
    vernacular_name
    """,
    )

    assert result.citation == None
    assert len(result.tables) == 1
    assert result.tables[0].page == 1
    assert result.tables[0].rows == [
        {
            "common_name": "Sunflower",
            "scientific_name": "Helianthus annuus",
            "species": "annuus",
        },
        {
            "common_name": "Rose",
            "scientific_name": "Rosa gallica",
            "species": "gallica",
        },
        {
            "common_name": "Tulip",
            "scientific_name": "Tulipa gesneriana",
            "species": "gesneriana",
        },
        {
            "common_name": "Lavender",
            "scientific_name": "Lavandula angustifolia",
            "species": "angustifolia",
        },
        {
            "common_name": "Oak",
            "scientific_name": "Quercus robur",
            "species": "robur",
        },
        {
            "common_name": "Maple",
            "scientific_name": "Acer saccharum",
            "species": "saccharum",
        },
        {
            "common_name": "Dandelion",
            "scientific_name": "Taraxacum officinale",
            "species": "officinale",
        },
        {
            "common_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
            "species": "vulgaris",
        },
        {
            "common_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia ficus-indica",
            "species": "ficus-indica",
        },
        {
            "common_name": "Coffee",
            "scientific_name": "Coffea arabica",
            "species": "arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_mapping_that_matches_page():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        mapping=TablesMapping(
            tables=[
                TableMapping(
                    title="Plants",
                    header_mode="all_pages",
                    first_page=1,
                    last_page=1,
                    column_mappings=[
                        ColumnMapping(
                            from_column_number=0, to_column_name="vernacular_name"
                        ),
                        ColumnMapping(
                            from_column_number=1, to_column_name="scientific_name"
                        ),
                    ],
                )
            ],
            citation="A citation",
        ),
    )

    assert result.citation == "A citation"
    assert len(result.tables) == 1
    assert result.tables[0].title == "Plants"
    assert result.tables[0].page == 1
    assert result.tables[0].rows == [
        {
            "vernacular_name": "Sunflower",
            "scientific_name": "Helianthus annuus",
        },
        {
            "vernacular_name": "Rose",
            "scientific_name": "Rosa gallica",
        },
        {
            "vernacular_name": "Tulip",
            "scientific_name": "Tulipa gesneriana",
        },
        {
            "vernacular_name": "Lavender",
            "scientific_name": "Lavandula angustifolia",
        },
        {
            "vernacular_name": "Oak",
            "scientific_name": "Quercus robur",
        },
        {
            "vernacular_name": "Maple",
            "scientific_name": "Acer saccharum",
        },
        {
            "vernacular_name": "Dandelion",
            "scientific_name": "Taraxacum officinale",
        },
        {
            "vernacular_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
        },
        {
            "vernacular_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia ficus-indica",
        },
        {
            "vernacular_name": "Coffee",
            "scientific_name": "Coffea arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_mapping_without_headers():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        mapping=TablesMapping(
            tables=[
                TableMapping(
                    title="Plants",
                    header_mode="none",
                    first_page=1,
                    last_page=1,
                    column_mappings=[
                        ColumnMapping(
                            from_column_number=0, to_column_name="vernacular_name"
                        ),
                        ColumnMapping(
                            from_column_number=1, to_column_name="scientific_name"
                        ),
                    ],
                )
            ],
            citation="A citation",
        ),
    )

    assert result.citation == "A citation"
    assert len(result.tables) == 1
    assert result.tables[0].title == "Plants"
    assert result.tables[0].page == 1
    assert result.tables[0].rows == [
        {
            "vernacular_name": "Sunflower",
            "scientific_name": "Helianthus annuus",
        },
        {
            "vernacular_name": "Rose",
            "scientific_name": "Rosa gallica",
        },
        {
            "vernacular_name": "Tulip",
            "scientific_name": "Tulipa gesneriana",
        },
        {
            "vernacular_name": "Lavender",
            "scientific_name": "Lavandula angustifolia",
        },
        {
            "vernacular_name": "Oak",
            "scientific_name": "Quercus robur",
        },
        {
            "vernacular_name": "Maple",
            "scientific_name": "Acer saccharum",
        },
        {
            "vernacular_name": "Dandelion",
            "scientific_name": "Taraxacum officinale",
        },
        {
            "vernacular_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
        },
        {
            "vernacular_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia ficus-indica",
        },
        {
            "vernacular_name": "Coffee",
            "scientific_name": "Coffea arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_mapping_that_doesnt_matches_page():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        mapping=TablesMapping(
            tables=[
                TableMapping(
                    title="Plants",
                    header_mode="all_pages",
                    first_page=2,
                    last_page=2,
                    column_mappings=[
                        ColumnMapping(
                            from_column_number=0, to_column_name="vernacular_name"
                        ),
                        ColumnMapping(
                            from_column_number=1, to_column_name="scientific_name"
                        ),
                    ],
                )
            ],
            citation="A citation",
        ),
    )

    assert result.citation == "A citation"
    assert len(result.tables) == 0


def test_read_table_with_mapping_and_page_offset():
    result = read_tables(
        "./tests/data/demo_table_p10.pdf",
        mapping=TablesMapping(
            tables=[
                TableMapping(
                    title="Plants",
                    header_mode="all_pages",
                    first_page=1,
                    last_page=1,
                    column_mappings=[
                        ColumnMapping(
                            from_column_number=0, to_column_name="vernacular_name"
                        ),
                        ColumnMapping(
                            from_column_number=1, to_column_name="scientific_name"
                        ),
                    ],
                )
            ],
            citation="A citation",
        ),
    )

    assert result.citation == "A citation"
    assert len(result.tables) == 1
    assert result.tables[0].title == "Plants"
    assert result.tables[0].rows == [
        {"vernacular_name": "Sunflower", "scientific_name": "Helianthus annuus"},
        {"vernacular_name": "Rose", "scientific_name": "Rosa gallica"},
        {"vernacular_name": "Tulip", "scientific_name": "Tulipa gesneriana"},
        {"vernacular_name": "Lavender", "scientific_name": "Lavandula angustifolia"},
        {"vernacular_name": "Oak", "scientific_name": "Quercus robur"},
        {"vernacular_name": "Maple", "scientific_name": "Acer saccharum"},
        {"vernacular_name": "Dandelion", "scientific_name": "Taraxacum officinale"},
        {"vernacular_name": "Bamboo", "scientific_name": "Bambusa vulgaris"},
        {"vernacular_name": "Cactus (Prickly Pear)", "scientific_name": "Opuntia ficus-indica"},
        {"vernacular_name": "Coffee", "scientific_name": "Coffea arabica"},
    ]


def test_read_table_with_mapping_and_page_offset_out_of_bounds():
    result = read_tables(
        "./tests/data/demo_table_p10.pdf",
        mapping=TablesMapping(
            tables=[
                TableMapping(
                    title="Plants",
                    header_mode="all_pages",
                    first_page=2,
                    last_page=2,
                    column_mappings=[
                        ColumnMapping(
                            from_column_number=0, to_column_name="vernacular_name"
                        ),
                    ],
                )
            ],
            citation="A citation",
        ),
    )

    assert result.citation == "A citation"
    assert len(result.tables) == 0
