import pytest
from paper2table.readers.pdfplumber import (
    read_tables,
    TableSchema,
    TablesSchema,
    ColumnMapping,
)


def test_read_table_without_options():
    result = read_tables("./tests/data/demo_table.pdf")

    assert result.citation == None
    assert len(result.tables) == 1
    assert result.tables[0].page == 1
    assert result.tables[0].rows == [
        {
            "0": "common_name",
            "1": "scienti\x00c_name",  # FIXME encoding is broken
            "2": "species",
        },
        {
            "0": "Sun\x00ower",
            "1": "Helianthus annuus",
            "2": "annuus",
        },
        {
            "0": "Rose",
            "1": "Rosa gallica",
            "2": "gallica",
        },
        {
            "0": "Tulip",
            "1": "Tulipa gesneriana",
            "2": "gesneriana",
        },
        {
            "0": "Lavender",
            "1": "Lavandula angustifolia",
            "2": "angustifolia",
        },
        {
            "0": "Oak",
            "1": "Quercus robur",
            "2": "robur",
        },
        {
            "0": "Maple",
            "1": "Acer saccharum",
            "2": "saccharum",
        },
        {
            "0": "Dandelion",
            "1": "Taraxacum o\x00cinale",
            "2": "o\x00cinale",
        },
        {
            "0": "Bamboo",
            "1": "Bambusa vulgaris",
            "2": "vulgaris",
        },
        {
            "0": "Cactus (Prickly Pear)",
            "1": "Opuntia \x00cus-indica",
            "2": "\x00cus-indica",
        },
        {
            "0": "Coffee",
            "1": "Coffea arabica",
            "2": "arabica",
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
            "common_name": "Sun\x00ower",
            "scienti_c_name": "Helianthus annuus",
            "species": "annuus",
        },
        {
            "common_name": "Rose",
            "scienti_c_name": "Rosa gallica",
            "species": "gallica",
        },
        {
            "common_name": "Tulip",
            "scienti_c_name": "Tulipa gesneriana",
            "species": "gesneriana",
        },
        {
            "common_name": "Lavender",
            "scienti_c_name": "Lavandula angustifolia",
            "species": "angustifolia",
        },
        {
            "common_name": "Oak",
            "scienti_c_name": "Quercus robur",
            "species": "robur",
        },
        {
            "common_name": "Maple",
            "scienti_c_name": "Acer saccharum",
            "species": "saccharum",
        },
        {
            "common_name": "Dandelion",
            "scienti_c_name": "Taraxacum o\x00cinale",
            "species": "o\x00cinale",
        },
        {
            "common_name": "Bamboo",
            "scienti_c_name": "Bambusa vulgaris",
            "species": "vulgaris",
        },
        {
            "common_name": "Cactus (Prickly Pear)",
            "scienti_c_name": "Opuntia \x00cus-indica",
            "species": "\x00cus-indica",
        },
        {
            "common_name": "Coffee",
            "scienti_c_name": "Coffea arabica",
            "species": "arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_schema_that_matches_page():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        schema=TablesSchema(
            tables=[
                TableSchema(
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
            "vernacular_name": "Sun\x00ower",
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
            "scientific_name": "Taraxacum o\x00cinale",
        },
        {
            "vernacular_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
        },
        {
            "vernacular_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia \x00cus-indica",
        },
        {
            "vernacular_name": "Coffee",
            "scientific_name": "Coffea arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_schema_without_headers():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        schema=TablesSchema(
            tables=[
                TableSchema(
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
            "scientific_name": "scienti\x00c_name",
            "vernacular_name": "common_name",
        },
        {
            "vernacular_name": "Sun\x00ower",
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
            "scientific_name": "Taraxacum o\x00cinale",
        },
        {
            "vernacular_name": "Bamboo",
            "scientific_name": "Bambusa vulgaris",
        },
        {
            "vernacular_name": "Cactus (Prickly Pear)",
            "scientific_name": "Opuntia \x00cus-indica",
        },
        {
            "vernacular_name": "Coffee",
            "scientific_name": "Coffea arabica",
        },
    ]
    result_dict = result.to_dict()
    assert result_dict["metadata"] == {"filename": "demo_table.pdf"}
    assert len(result_dict["tables"][0]["table_fragments"]) == 1


def test_read_table_with_schema_that_doesnt_matches_page():
    result = read_tables(
        "./tests/data/demo_table.pdf",
        schema=TablesSchema(
            tables=[
                TableSchema(
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
