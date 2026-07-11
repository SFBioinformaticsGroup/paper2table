from argparse import Namespace

from tablemerge.settings import MergeSettings
from utils.column_schema import ColumnSchema


def test_from_args_maps_fields_and_ignores_extras():
    args = Namespace(
        agreement_method="distinct-readers",
        drop_empty_columns=False,
        drop_empty_tables=True,
        only_semantic_columns=True,
        remove_header_rows=False,
        pretty=True,
        filter_title_rows=True,
        jaccard_column_alignment=True,
        column_alignment_threshold=0.7,
        column_name_semantic_alignment=False,
        column_value_semantic_alignment=False,
        semantic_language="es",
        hints_column_alignment=None,
        fix_reversed_column_values=False,
        strip_leading_row_numbers=False,
        normalize_punctuation=False,
        split_conjunction_columns=False,
        transform_tablesfile=None,
        filter_schema_columns=False,
        order_schema_columns=False,
        coerce_schema_column_types=False,
        column_aliases="familia:family",
        column_aliases_path=None,
        paper_aliases=None,
        paper_aliases_path=None,
        column_names_hints=None,
        column_names_hints_path=None,
        schema="family:str",
        schema_path=None,
        # extra args not in MergeSettings
        paths=["dir1", "dir2"],
        output_directory=".",
        metadata_only=False,
        export_settings=False,
        workers=4,
        paper=None,
        settings=False,
    )
    settings = MergeSettings.from_args(args)
    assert settings.agreement_method == "distinct-readers"
    assert settings.drop_empty_columns is False
    assert settings.jaccard_column_alignment is True
    assert settings.column_alignment_threshold == 0.7
    assert settings.semantic_language == "es"
    assert settings.column_aliases == "familia:family"
    assert settings.schema == "family:str"
    assert settings.paper_aliases is None


def test_from_args_reads_schema_from_path():
    args = Namespace(
        agreement_method="simple-count",
        drop_empty_columns=True,
        drop_empty_tables=True,
        only_semantic_columns=False,
        remove_header_rows=False,
        pretty=False,
        filter_title_rows=True,
        jaccard_column_alignment=False,
        column_alignment_threshold=0.5,
        column_name_semantic_alignment=False,
        column_value_semantic_alignment=False,
        semantic_language="en",
        hints_column_alignment=None,
        fix_reversed_column_values=False,
        strip_leading_row_numbers=False,
        normalize_punctuation=False,
        split_conjunction_columns=False,
        transform_tablesfile=None,
        filter_schema_columns=False,
        order_schema_columns=False,
        coerce_schema_column_types=False,
        column_aliases=None,
        column_aliases_path=None,
        paper_aliases=None,
        paper_aliases_path=None,
        column_names_hints=None,
        column_names_hints_path=None,
        schema=None,
        schema_path="tests/data/demo_schema.txt",
        paths=["dir1"],
        output_directory=".",
        metadata_only=False,
        export_settings=False,
        workers=1,
        paper=None,
        settings=False,
    )
    settings = MergeSettings.from_args(args)
    assert settings.schema == "name:str\nspecies:str"


def test_merge_settings_from_dict_defaults():
    settings = MergeSettings.from_dict({})
    assert settings == MergeSettings(
        agreement_method="simple-count",
        drop_empty_columns=True,
        drop_empty_tables=True,
        only_semantic_columns=False,
        remove_header_rows=False,
        column_names_hints=None,
        schema=None,
        paper_aliases=None,
    )


def test_from_dict_ignores_unknown_attributes():
    settings = MergeSettings.from_dict(
        {"agreement_method": "distinct-readers", "unknown_field": "ignored"}
    )
    assert settings.agreement_method == "distinct-readers"


def test_merge_settings_from_dict_simple_fields():
    settings = MergeSettings.from_dict(
        {
            "agreement_method": "distinct-readers",
            "drop_empty_columns": False,
            "drop_empty_tables": False,
            "only_semantic_columns": True,
            "remove_header_rows": True,
            "column_names_hints": ["species", "family"],
            "schema": {"family": "str", "count": "int"},
        }
    )
    assert settings.agreement_method == "distinct-readers"
    assert settings.drop_empty_columns is False
    assert settings.drop_empty_tables is False
    assert settings.only_semantic_columns is True
    assert settings.remove_header_rows is True
    assert settings.column_names_hints == ["species", "family"]
    assert settings.schema == {"family": "str", "count": "int"}


def test_to_dict_simple_fields():
    settings = MergeSettings.from_dict(
        {
            "agreement_method": "distinct-readers",
            "drop_empty_columns": False,
            "drop_empty_tables": True,
            "only_semantic_columns": True,
            "remove_header_rows": True,
        }
    )
    defaults = settings.to_dict()
    assert defaults["agreement_method"] == "distinct-readers"
    assert defaults["drop_empty_columns"] is False
    assert defaults["drop_empty_tables"] is True
    assert defaults["only_semantic_columns"] is True
    assert defaults["remove_header_rows"] is True


def test_to_dict_pretransformers():
    settings = MergeSettings.from_dict(
        {
            "filter_title_rows": True,
            "strip_leading_row_numbers": True,
        }
    )
    defaults = settings.to_dict()
    assert defaults["filter_title_rows"] is True
    assert defaults["strip_leading_row_numbers"] is True
    assert defaults["fix_reversed_column_values"] is False
    assert defaults["normalize_punctuation"] is False
    assert defaults["split_conjunction_columns"] is False


def test_to_dict_no_title_filter_when_absent():
    settings = MergeSettings.from_dict({"filter_title_rows": False})
    defaults = settings.to_dict()
    assert defaults["filter_title_rows"] is False


def test_to_dict_language_from_reverser():
    settings = MergeSettings.from_dict(
        {
            "semantic_language": "es",
            "fix_reversed_column_values": True,
        }
    )
    defaults = settings.to_dict()
    assert defaults["fix_reversed_column_values"] is True
    assert defaults["semantic_language"] == "es"


def test_to_dict_tablesfile_transformer_explode():
    settings = MergeSettings.from_dict({"transform_tablesfile": "explode"})
    assert settings.to_dict()["transform_tablesfile"] == "explode"


def test_to_dict_tablesfile_transformer_safe_compact():
    settings = MergeSettings.from_dict({"transform_tablesfile": "safe-compact"})
    assert settings.to_dict()["transform_tablesfile"] == "safe-compact"


def test_to_dict_tablesfile_transformer_unsafe_compact():
    settings = MergeSettings.from_dict({"transform_tablesfile": "unsafe-compact"})
    assert settings.to_dict()["transform_tablesfile"] == "unsafe-compact"


def test_to_dict_analyzers():
    settings = MergeSettings.from_dict(
        {
            "jaccard_column_alignment": True,
            "column_value_semantic_alignment": True,
            "column_name_semantic_alignment": False,
            "column_alignment_threshold": 0.7,
            "semantic_language": "es",
            "hints_column_alignment": "unsafe",
        }
    )
    defaults = settings.to_dict()
    assert defaults["jaccard_column_alignment"] is True
    assert defaults["column_value_semantic_alignment"] is True
    assert defaults["column_name_semantic_alignment"] is False
    assert defaults["column_alignment_threshold"] == 0.7
    assert defaults["semantic_language"] == "es"
    assert defaults["hints_column_alignment"] == "unsafe"


def test_to_dict_hints_safe_mode():
    settings = MergeSettings.from_dict({"hints_column_alignment": "safe"})
    defaults = settings.to_dict()
    assert defaults["hints_column_alignment"] == "safe"


def test_to_dict_postprocessors():
    settings = MergeSettings.from_dict(
        {
            "filter_schema_columns": True,
            "order_schema_columns": False,
            "coerce_schema_column_types": True,
        }
    )
    defaults = settings.to_dict()
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
