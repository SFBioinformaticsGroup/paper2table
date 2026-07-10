import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from utils.column_schema import ColumnSchema


@dataclass
class MergeSettings:
    agreement_method: str = "simple-count"
    drop_empty_columns: bool = True
    drop_empty_tables: bool = True
    only_semantic_columns: bool = False
    remove_header_rows: bool = False
    column_names_hints: list[str] = field(default_factory=list)
    schema: dict[str, str] = field(default_factory=dict)
    pretransformers: dict[str, dict] = field(default_factory=dict)
    tablesfile_transformer: dict = field(default_factory=dict)
    analyzers: dict[str, dict] = field(default_factory=dict)
    postprocessors: dict[str, dict] = field(default_factory=dict)
    paper_aliases: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "MergeSettings":
        return cls(
            agreement_method=data.get("agreement_method", "simple-count"),
            drop_empty_columns=data.get("drop_empty_columns", True),
            drop_empty_tables=data.get("drop_empty_tables", True),
            only_semantic_columns=data.get("only_semantic_columns", False),
            remove_header_rows=data.get("remove_header_rows", False),
            column_names_hints=data.get("column_names_hints", []),
            schema=data.get("schema", {}),
            pretransformers=data.get("pretransformers", {}),
            tablesfile_transformer=data.get("tablesfile_transformer", {}),
            analyzers=data.get("analyzers", {}),
            postprocessors=data.get("postprocessors", {}),
            paper_aliases=data.get("paper_aliases", {}),
        )

    def to_argparse_defaults(self) -> dict:
        defaults: dict = {}

        defaults["agreement_method"] = self.agreement_method
        defaults["drop_empty_columns"] = self.drop_empty_columns
        defaults["drop_empty_tables"] = self.drop_empty_tables
        defaults["only_semantic_columns"] = self.only_semantic_columns
        defaults["remove_header_rows"] = self.remove_header_rows

        if self.pretransformers:
            for setting, klass in {
                "filter_title_rows": "FilterTitleRowsTransformer",
                "fix_reversed_column_values": "FragmentValuesReverser",
                "strip_leading_row_numbers": "LeadingRowNumberTransformer",
                "normalize_punctuation": "NormalizePunctuationTransformer",
                "split_conjunction_columns": "SplitColumnTransformer",
            }.items():
                defaults[setting] = klass in self.pretransformers
            reverser = self.pretransformers.get("FragmentValuesReverser", {})
            splitter = self.pretransformers.get("SplitColumnTransformer", {})
            language = reverser.get("language") or splitter.get("language")
            if language:
                defaults["semantic_language"] = language

        tablesfiles_transformers = {
            "exploder": "explode",
            "compact-safe": "safe-compact",
            "compact-unsafe": "unsafe-compact",
        }
        tf_type = tablesfiles_transformers.get(
            self.tablesfile_transformer.get("type", "")
        )
        if tf_type:
            defaults["transform_tablesfile"] = tf_type

        if self.analyzers:
            for setting, klass in {
                "jaccard_column_alignment": "JaccardMergeTimeAnalyzer",
                "column_name_semantic_alignment": "ColumnNameSemanticLoadTimeAnalyzer",
                "column_value_semantic_alignment": "ColumnValueSemanticMergeTimeAnalyzer",
            }.items():
                defaults[setting] = klass in self.analyzers

            if "HintsLoadTimeAnalyzer" in self.analyzers:
                safe = self.analyzers["HintsLoadTimeAnalyzer"].get("safe", True)
                defaults["hints_column_alignment"] = "safe" if safe else "unsafe"

            for analyzer_name in (
                "JaccardMergeTimeAnalyzer",
                "ColumnNameSemanticLoadTimeAnalyzer",
                "ColumnValueSemanticMergeTimeAnalyzer",
            ):
                analyzer = self.analyzers.get(analyzer_name, {})
                if "threshold" in analyzer:
                    defaults.setdefault(
                        "column_alignment_threshold", analyzer["threshold"]
                    )
                if "language" in analyzer:
                    defaults.setdefault("semantic_language", analyzer["language"])

        schema_postprocessor = self.postprocessors.get("SchemaPostProcessor", {})
        if schema_postprocessor:
            for setting in [
                "filter_schema_columns",
                "order_schema_columns",
                "coerce_schema_column_types",
            ]:
                if setting in schema_postprocessor:
                    defaults[setting] = schema_postprocessor[setting]

        if self.schema:
            defaults["schema"] = ",".join(f"{k}:{v}" for k, v in self.schema.items())

        if self.column_names_hints:
            defaults["column_names_hints"] = " ".join(self.column_names_hints)

        alias_settings = self.analyzers.get("AliasLoadTimeAnalyzer", {})
        if alias_settings.get("aliases"):
            defaults["column_aliases"] = " ".join(
                f"{k}:{v}" for k, v in alias_settings["aliases"].items()
            )

        if self.paper_aliases:
            parts = []
            for alias_name, data in self.paper_aliases.items():
                canonical = data["canonical"]
                offset = data.get("offset", 0)
                parts.append(
                    f"{alias_name}:{canonical}:{offset}"
                    if offset
                    else f"{alias_name}:{canonical}"
                )
            defaults["paper_aliases"] = " ".join(parts)

        return defaults


def build_export_settings(args, schema: Optional[ColumnSchema], hints: list[str], aliases: dict[str, str], paper_aliases: dict) -> dict:
    pretransformers = {}
    if args.fix_reversed_column_values:
        pretransformers["FragmentValuesReverser"] = {"language": args.semantic_language}
    if args.filter_title_rows:
        pretransformers["FilterTitleRowsTransformer"] = {}
    if args.strip_leading_row_numbers:
        pretransformers["LeadingRowNumberTransformer"] = {}
    if args.normalize_punctuation:
        pretransformers["NormalizePunctuationTransformer"] = {}
    if args.split_conjunction_columns:
        pretransformers["SplitColumnTransformer"] = {"language": args.semantic_language}
    pretransformers["FilterEmptyRowsTransformer"] = {}

    tf_reverse_map = {
        "explode": "exploder",
        "safe-compact": "compact-safe",
        "unsafe-compact": "compact-unsafe",
    }
    tablesfile_transformer: dict = {}
    if args.transform_tablesfile in tf_reverse_map:
        tablesfile_transformer = {"type": tf_reverse_map[args.transform_tablesfile]}

    analyzers: dict = {}
    if args.hints_column_alignment and hints:
        analyzers["HintsLoadTimeAnalyzer"] = {"safe": args.hints_column_alignment == "safe"}
    if aliases:
        analyzers["AliasLoadTimeAnalyzer"] = {"aliases": aliases}
    if args.column_name_semantic_alignment:
        analyzers["ColumnNameSemanticLoadTimeAnalyzer"] = {
            "threshold": args.column_alignment_threshold,
            "language": args.semantic_language,
        }
    if args.jaccard_column_alignment:
        analyzers["JaccardMergeTimeAnalyzer"] = {
            "threshold": args.column_alignment_threshold,
            "schema": bool(schema),
        }
    if args.column_value_semantic_alignment:
        analyzers["ColumnValueSemanticMergeTimeAnalyzer"] = {
            "threshold": args.column_alignment_threshold,
            "language": args.semantic_language,
            "schema": bool(schema),
        }

    postprocessors: dict = {}
    if any([args.filter_schema_columns, args.order_schema_columns, args.coerce_schema_column_types]):
        postprocessors["SchemaPostProcessor"] = {
            "filter_schema_columns": args.filter_schema_columns,
            "order_schema_columns": args.order_schema_columns,
            "coerce_schema_column_types": args.coerce_schema_column_types,
        }

    return {
        "agreement_method": args.agreement_method,
        "pretransformers": pretransformers,
        "tablesfile_transformer": tablesfile_transformer,
        "drop_empty_columns": args.drop_empty_columns,
        "drop_empty_tables": args.drop_empty_tables,
        "only_semantic_columns": args.only_semantic_columns,
        "remove_header_rows": args.remove_header_rows,
        "column_names_hints": hints,
        "schema": schema.serialize() if schema else {},
        "analyzers": analyzers,
        "postprocessors": postprocessors,
        "paper_aliases": {
            k: {"canonical": v.canonical, "offset": v.offset}
            for k, v in paper_aliases.items()
        },
    }


def write_settings_file(settings: dict, output_path: Path) -> Path:
    settings_file_path = output_path / "settings.tablemerge.json"
    with open(settings_file_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    return settings_file_path


def read_settings_file(output_path: Path) -> MergeSettings:
    settings_file_path =  output_path / "settings.tablemerge.json"
    with open(settings_file_path, encoding="utf-8") as f:
        return MergeSettings.from_dict(json.load(f))

