from utils.tokenize_schema import tokenize_schema
from utils.column_schema import ColumnSchema
from tablemerge.aliases import parse_column_aliases


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
    schema = ColumnSchema.parse("family:str # ignored\nspecies:int")
    assert schema.column_names() == ["family", "species"]
    assert schema.column_type("family") is str
    assert schema.column_type("species") is int


def test_parse_column_aliases_ignores_comments():
    text = "# rename columns\nfamilia:family # Spanish\nespecie:species"
    assert parse_column_aliases(text) == {"familia": "family", "especie": "species"}
