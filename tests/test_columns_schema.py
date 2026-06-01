from utils.columns_schema import tokenize_schema, parse_schema
from tablemerge.__main__ import parse_aliases


def test_tokenize_schema_basic():
    assert tokenize_schema("family:str species:str") == ["family:str", "species:str"]


def test_tokenize_schema_comma_separated():
    assert tokenize_schema("family:str,species:str") == ["family:str", "species:str"]


def test_tokenize_schema_ignores_full_line_comment():
    assert tokenize_schema("# this is a comment\nfamily:str") == ["family:str"]


def test_tokenize_schema_ignores_inline_comment():
    assert tokenize_schema("family:str # the family column\nspecies:str") == [
        "family:str",
        "species:str",
    ]


def test_tokenize_schema_ignores_comment_only_lines():
    text = """
# header comment
family:str
# mid comment
species:str
"""
    assert tokenize_schema(text) == ["family:str", "species:str"]


def test_parse_schema_ignores_comments():
    schema = parse_schema("family:str # ignored\nspecies:int")
    assert schema == {"family": (str, ...), "species": (int, ...)}


def test_parse_aliases_ignores_comments():
    text = "# rename columns\nfamilia:family # Spanish\nespecie:species"
    assert parse_aliases(text) == {"familia": "family", "especie": "species"}
