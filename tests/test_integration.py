import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_paper2table(*args):
    result = subprocess.run(
        [sys.executable, "-m", "paper2table", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    return json.loads(result.stdout)


def test_pdfplumber_cli():
    result = run_paper2table(
        "-r",
        "pdfplumber",
        "-p",
        "tests/data/demo_column_hints.txt",
        "tests/data/demo_table.pdf",
    )
    assert result == {
        "tables": [
            {
                "table_fragments": [
                    {
                        "rows": [
                            {
                                "0": "common_name",
                                "1": "scienti\x00c_name",
                                "2": "species",
                            },
                            {
                                "0": "Sun\x00ower",
                                "1": "Helianthus annuus",
                                "2": "annuus",
                            },
                            {"0": "Rose", "1": "Rosa gallica", "2": "gallica"},
                            {"0": "Tulip", "1": "Tulipa gesneriana", "2": "gesneriana"},
                            {
                                "0": "Lavender",
                                "1": "Lavandula angustifolia",
                                "2": "angustifolia",
                            },
                            {"0": "Oak", "1": "Quercus robur", "2": "robur"},
                            {"0": "Maple", "1": "Acer saccharum", "2": "saccharum"},
                            {
                                "0": "Dandelion",
                                "1": "Taraxacum o\x00cinale",
                                "2": "o\x00cinale",
                            },
                            {"0": "Bamboo", "1": "Bambusa vulgaris", "2": "vulgaris"},
                            {
                                "0": "Cactus (Prickly Pear)",
                                "1": "Opuntia \x00cus-indica",
                                "2": "\x00cus-indica",
                            },
                            {"0": "Coffee", "1": "Coffea arabica", "2": "arabica"},
                        ],
                        "page": 1,
                    }
                ]
            }
        ],
        "citation": None,
        "metadata": {"filename": "demo_table.pdf"},
    }


def test_camelot_cli():
    result = run_paper2table(
        "-r",
        "camelot",
        "-p",
        "tests/data/demo_column_hints.txt",
        "tests/data/demo_table.pdf",
    )
    assert result == {
        "tables": [
            {
                "table_fragments": [
                    {
                        "rows": [
                            {"0": "This is an interesting table:", "1": "", "2": ""},
                            {
                                "0": "common_name",
                                "1": "scienti\x00c_name",
                                "2": "species",
                            },
                            {
                                "0": "Sun\x00ower",
                                "1": "Helianthus annuus",
                                "2": "annuus",
                            },
                            {"0": "Rose", "1": "Rosa gallica", "2": "gallica"},
                            {"0": "Tulip", "1": "Tulipa gesneriana", "2": "gesneriana"},
                            {
                                "0": "Lavender",
                                "1": "Lavandula angustifolia",
                                "2": "angustifolia",
                            },
                            {"0": "Oak", "1": "Quercus robur", "2": "robur"},
                            {"0": "Maple", "1": "Acer saccharum", "2": "saccharum"},
                            {
                                "0": "Dandelion",
                                "1": "Taraxacum o\x00cinale",
                                "2": "o\x00cinale",
                            },
                            {"0": "Bamboo", "1": "Bambusa vulgaris", "2": "vulgaris"},
                            {
                                "0": "Cactus (Prickly Pear)",
                                "1": "Opuntia \x00cus-indica",
                                "2": "\x00cus-indica",
                            },
                            {"0": "Coffee", "1": "Coffea arabica", "2": "arabica"},
                        ],
                        "page": 1,
                    }
                ]
            }
        ],
        "citation": None,
        "metadata": {"filename": "demo_table.pdf"},
    }


def test_pymupdf_cli():
    result = run_paper2table(
        "-r",
        "pymupdf",
        "-p",
        "tests/data/demo_column_hints.txt",
        "tests/data/demo_table.pdf",
    )
    assert result == {
        "tables": [
            {
                "table_fragments": [
                    {
                        "rows": [
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
                        ],
                        "page": 1,
                    }
                ]
            }
        ],
        "citation": None,
        "metadata": {"filename": "demo_table.pdf"},
    }


def test_hybrid_pymupdf_cli():
    # Uses a pre-existing mapping file to avoid hitting the Gemini API.
    # The mapping lives in tests/data/mappings/demo_table.mapping.json.
    result = run_paper2table(
        "-H",
        "-r",
        "pymupdf",
        "-p",
        "tests/data/demo_schema.txt",
        "-M",
        "tests/data/mappings",
        "tests/data/demo_table.pdf",
    )
    assert result == {
        "tables": [
            {
                "table_fragments": [
                    {
                        "rows": [
                            {"name": "Sunflower", "species": "annuus"},
                            {"name": "Rose", "species": "gallica"},
                            {"name": "Tulip", "species": "gesneriana"},
                            {"name": "Lavender", "species": "angustifolia"},
                            {"name": "Oak", "species": "robur"},
                            {"name": "Maple", "species": "saccharum"},
                            {"name": "Dandelion", "species": "officinale"},
                            {"name": "Bamboo", "species": "vulgaris"},
                            {"name": "Cactus (Prickly Pear)", "species": "ficus-indica"},
                            {"name": "Coffee", "species": "arabica"},
                        ],
                        "page": 1,
                        "title": "Plant Species Information",
                    }
                ]
            }
        ],
        "citation": "N/A",
        "metadata": {"filename": "demo_table.pdf"},
    }
