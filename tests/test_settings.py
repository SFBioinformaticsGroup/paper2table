from tablemerge.settings import MergeSettings
from utils.column_schema import ColumnSchema


def test_merge_settings_from_dict_defaults():
    settings = MergeSettings.from_dict({})
    assert settings == MergeSettings(
        agreement_method="simple-count",
        drop_empty_columns=True,
        drop_empty_tables=True,
        only_semantic_columns=False,
        remove_header_rows=False,
        column_names_hints=[],
        schema={},
        pretransformers={},
        tablesfile_transformer={},
        analyzers={},
        postprocessors={},
        paper_aliases={},
    )


def test_merge_settings_from_dict_simple_fields():
    settings = MergeSettings.from_dict({
        "agreement_method": "distinct-readers",
        "drop_empty_columns": False,
        "drop_empty_tables": False,
        "only_semantic_columns": True,
        "remove_header_rows": True,
        "column_names_hints": ["species", "family"],
        "schema": {"family": "str", "count": "int"},
    })
    assert settings.agreement_method == "distinct-readers"
    assert settings.drop_empty_columns is False
    assert settings.drop_empty_tables is False
    assert settings.only_semantic_columns is True
    assert settings.remove_header_rows is True
    assert settings.column_names_hints == ["species", "family"]
    assert settings.schema == {"family": "str", "count": "int"}


def test_to_argparse_defaults_simple_fields():
    settings = MergeSettings.from_dict({
        "agreement_method": "distinct-readers",
        "drop_empty_columns": False,
        "drop_empty_tables": True,
        "only_semantic_columns": True,
        "remove_header_rows": True,
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["agreement_method"] == "distinct-readers"
    assert defaults["drop_empty_columns"] is False
    assert defaults["drop_empty_tables"] is True
    assert defaults["only_semantic_columns"] is True
    assert defaults["remove_header_rows"] is True


def test_to_argparse_defaults_pretransformers():
    settings = MergeSettings.from_dict({
        "pretransformers": {
            "FilterTitleRowsTransformer": {"enabled": True},
            "LeadingRowNumberTransformer": {"enabled": True},
            "FilterEmptyRowsTransformer": {"enabled": True},
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["filter_title_rows"] is True
    assert defaults["strip_leading_row_numbers"] is True
    assert defaults["fix_reversed_column_values"] is False
    assert defaults["normalize_punctuation"] is False
    assert defaults["split_conjunction_columns"] is False


def test_to_argparse_defaults_no_title_filter_when_absent():
    settings = MergeSettings.from_dict({
        "pretransformers": {
            "FilterEmptyRowsTransformer": {"enabled": True},
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["filter_title_rows"] is False


def test_to_argparse_defaults_language_from_reverser():
    settings = MergeSettings.from_dict({
        "pretransformers": {
            "FragmentValuesReverser": {"language": "es"},
            "FilterEmptyRowsTransformer": {"enabled": True},
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["fix_reversed_column_values"] is True
    assert defaults["semantic_language"] == "es"


def test_to_argparse_defaults_tablesfile_transformer_explode():
    settings = MergeSettings.from_dict({"tablesfile_transformer": {"type": "exploder"}})
    assert settings.to_argparse_defaults()["transform_tablesfile"] == "explode"


def test_to_argparse_defaults_tablesfile_transformer_safe_compact():
    settings = MergeSettings.from_dict({"tablesfile_transformer": {"type": "compact-safe"}})
    assert settings.to_argparse_defaults()["transform_tablesfile"] == "safe-compact"


def test_to_argparse_defaults_tablesfile_transformer_unsafe_compact():
    settings = MergeSettings.from_dict({"tablesfile_transformer": {"type": "compact-unsafe"}})
    assert settings.to_argparse_defaults()["transform_tablesfile"] == "unsafe-compact"


def test_to_argparse_defaults_tablesfile_transformer_null():
    settings = MergeSettings.from_dict({"tablesfile_transformer": {}})
    assert "transform_tablesfile" not in settings.to_argparse_defaults()


def test_to_argparse_defaults_analyzers():
    settings = MergeSettings.from_dict({
        "analyzers": {
            "JaccardMergeTimeAnalyzer": {"threshold": 0.7, "schema": False},
            "ColumnValueSemanticMergeTimeAnalyzer": {"threshold": 0.7, "language": "es", "schema": False},
            "HintsLoadTimeAnalyzer": {"hints": True, "safe": False},
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["jaccard_column_alignment"] is True
    assert defaults["column_value_semantic_alignment"] is True
    assert defaults["column_name_semantic_alignment"] is False
    assert defaults["column_alignment_threshold"] == 0.7
    assert defaults["semantic_language"] == "es"
    assert defaults["hints_column_alignment"] == "unsafe"


def test_to_argparse_defaults_hints_safe_mode():
    settings = MergeSettings.from_dict({
        "analyzers": {
            "HintsLoadTimeAnalyzer": {"hints": True, "safe": True},
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["hints_column_alignment"] == "safe"


def test_to_argparse_defaults_postprocessors():
    settings = MergeSettings.from_dict({
        "postprocessors": {
            "SchemaPostProcessor": {
                "filter_schema_columns": True,
                "order_schema_columns": False,
                "coerce_schema_column_types": True,
            }
        }
    })
    defaults = settings.to_argparse_defaults()
    assert defaults["filter_schema_columns"] is True
    assert defaults["order_schema_columns"] is False
    assert defaults["coerce_schema_column_types"] is True


def test_column_schema_from_settings_dict_empty():
    result = ColumnSchema.from_settings_dict({})
    assert result is None


def test_column_schema_from_settings_dict_round_trip():
    original_schema = ColumnSchema.parse("family:str,count:int,name:scientific_name")
    serialized = original_schema.serialize()
    reconstructed = ColumnSchema.from_settings_dict(serialized)
    assert reconstructed is not None
    assert reconstructed.serialize() == serialized


def test_column_schema_from_settings_dict_single_field():
    schema = ColumnSchema.from_settings_dict({"family": "str"})
    assert schema is not None
    assert schema.serialize() == {"family": "str"}
