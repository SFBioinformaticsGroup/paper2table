import dataclasses
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
    pretty: bool = False
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
            pretty=data.get("pretty", False),
            column_names_hints=data.get("column_names_hints", []),
            schema=data.get("schema", {}),
            pretransformers=data.get("pretransformers", {}),
            tablesfile_transformer=data.get("tablesfile_transformer", {}),
            analyzers=data.get("analyzers", {}),
            postprocessors=data.get("postprocessors", {}),
            paper_aliases=data.get("paper_aliases", {}),
        )

    @classmethod
    def from_args(
        cls,
        args,
        schema: Optional[ColumnSchema],
        hints: list[str],
        aliases: dict[str, str],
        paper_aliases: dict,
    ) -> "MergeSettings":
        return cls(
            agreement_method=args.agreement_method,
            drop_empty_columns=args.drop_empty_columns,
            drop_empty_tables=args.drop_empty_tables,
            only_semantic_columns=args.only_semantic_columns,
            remove_header_rows=args.remove_header_rows,
            pretty=args.pretty,
            column_names_hints=hints,
            schema=schema.serialize() if schema else {},
            pretransformers=cls._pretransformers_from_args(args),
            tablesfile_transformer=cls._tablesfile_transformer_from_args(args),
            analyzers=cls._analyzers_from_args(args, schema, aliases, hints),
            postprocessors=cls._postprocessors_from_args(args),
            paper_aliases={
                alias_name: {
                    "canonical": paper_alias.canonical,
                    "offset": paper_alias.offset,
                }
                for alias_name, paper_alias in paper_aliases.items()
            },
        )

    @staticmethod
    def _pretransformers_from_args(args) -> dict:
        pretransformers = {}
        if args.fix_reversed_column_values:
            pretransformers["FragmentValuesReverser"] = {
                "language": args.semantic_language
            }
        if args.filter_title_rows:
            pretransformers["FilterTitleRowsTransformer"] = {}
        if args.strip_leading_row_numbers:
            pretransformers["LeadingRowNumberTransformer"] = {}
        if args.normalize_punctuation:
            pretransformers["NormalizePunctuationTransformer"] = {}
        if args.split_conjunction_columns:
            pretransformers["SplitColumnTransformer"] = {
                "language": args.semantic_language
            }
        pretransformers["FilterEmptyRowsTransformer"] = {}
        return pretransformers

    @staticmethod
    def _tablesfile_transformer_from_args(args) -> dict:
        cli_value_to_settings_type = {
            "explode": "exploder",
            "safe-compact": "compact-safe",
            "unsafe-compact": "compact-unsafe",
        }
        settings_type = cli_value_to_settings_type.get(args.transform_tablesfile)
        return {"type": settings_type} if settings_type else {}

    @staticmethod
    def _analyzers_from_args(
        args,
        schema: Optional[ColumnSchema],
        aliases: dict[str, str],
        hints: list[str],
    ) -> dict:
        analyzers = {}
        if args.hints_column_alignment and hints:
            analyzers["HintsLoadTimeAnalyzer"] = {
                "safe": args.hints_column_alignment == "safe"
            }
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
        return analyzers

    @staticmethod
    def _postprocessors_from_args(args) -> dict:
        if any(
            (
                args.filter_schema_columns,
                args.order_schema_columns,
                args.coerce_schema_column_types,
            )
        ):
            return {
                "SchemaPostProcessor": {
                    "filter_schema_columns": args.filter_schema_columns,
                    "order_schema_columns": args.order_schema_columns,
                    "coerce_schema_column_types": args.coerce_schema_column_types,
                }
            }
        return {}

    def to_argparse_defaults(self) -> dict:
        defaults: dict = {}
        self._apply_basic_flags(defaults)
        self._apply_pretransformer_flags(defaults)
        self._apply_tablesfile_transformer_flags(defaults)
        self._apply_analyzer_flags(defaults)
        self._apply_postprocessor_flags(defaults)
        self._apply_schema_flags(defaults)
        self._apply_hints_flags(defaults)
        self._apply_column_aliases_flags(defaults)
        self._apply_paper_aliases_flags(defaults)
        return defaults

    def _apply_basic_flags(self, defaults: dict) -> None:
        defaults["agreement_method"] = self.agreement_method
        defaults["drop_empty_columns"] = self.drop_empty_columns
        defaults["drop_empty_tables"] = self.drop_empty_tables
        defaults["only_semantic_columns"] = self.only_semantic_columns
        defaults["remove_header_rows"] = self.remove_header_rows
        defaults["pretty"] = self.pretty

    def _apply_pretransformer_flags(self, defaults: dict) -> None:
        if not self.pretransformers:
            return
        for flag_name, class_name in {
            "filter_title_rows": "FilterTitleRowsTransformer",
            "fix_reversed_column_values": "FragmentValuesReverser",
            "strip_leading_row_numbers": "LeadingRowNumberTransformer",
            "normalize_punctuation": "NormalizePunctuationTransformer",
            "split_conjunction_columns": "SplitColumnTransformer",
        }.items():
            defaults[flag_name] = class_name in self.pretransformers
        reverser = self.pretransformers.get("FragmentValuesReverser", {})
        splitter = self.pretransformers.get("SplitColumnTransformer", {})
        language = reverser.get("language") or splitter.get("language")
        if language:
            defaults["semantic_language"] = language

    def _apply_tablesfile_transformer_flags(self, defaults: dict) -> None:
        settings_type_to_cli_value = {
            "exploder": "explode",
            "compact-safe": "safe-compact",
            "compact-unsafe": "unsafe-compact",
        }
        cli_value = settings_type_to_cli_value.get(
            self.tablesfile_transformer.get("type", "")
        )
        if cli_value:
            defaults["transform_tablesfile"] = cli_value

    def _apply_analyzer_flags(self, defaults: dict) -> None:
        if not self.analyzers:
            return
        for flag_name, class_name in {
            "jaccard_column_alignment": "JaccardMergeTimeAnalyzer",
            "column_name_semantic_alignment": "ColumnNameSemanticLoadTimeAnalyzer",
            "column_value_semantic_alignment": "ColumnValueSemanticMergeTimeAnalyzer",
        }.items():
            defaults[flag_name] = class_name in self.analyzers

        if "HintsLoadTimeAnalyzer" in self.analyzers:
            is_safe = self.analyzers["HintsLoadTimeAnalyzer"].get("safe", True)
            defaults["hints_column_alignment"] = "safe" if is_safe else "unsafe"

        for analyzer_name in (
            "JaccardMergeTimeAnalyzer",
            "ColumnNameSemanticLoadTimeAnalyzer",
            "ColumnValueSemanticMergeTimeAnalyzer",
        ):
            analyzer = self.analyzers.get(analyzer_name, {})
            if "threshold" in analyzer:
                defaults.setdefault("column_alignment_threshold", analyzer["threshold"])
            if "language" in analyzer:
                defaults.setdefault("semantic_language", analyzer["language"])

    def _apply_postprocessor_flags(self, defaults: dict) -> None:
        schema_postprocessor = self.postprocessors.get("SchemaPostProcessor", {})
        for flag_name in (
            "filter_schema_columns",
            "order_schema_columns",
            "coerce_schema_column_types",
        ):
            if flag_name in schema_postprocessor:
                defaults[flag_name] = schema_postprocessor[flag_name]

    def _apply_schema_flags(self, defaults: dict) -> None:
        if self.schema:
            defaults["schema"] = ",".join(f"{k}:{v}" for k, v in self.schema.items())

    def _apply_hints_flags(self, defaults: dict) -> None:
        if self.column_names_hints:
            defaults["column_names_hints"] = " ".join(self.column_names_hints)

    def _apply_column_aliases_flags(self, defaults: dict) -> None:
        alias_analyzer = self.analyzers.get("AliasLoadTimeAnalyzer", {})
        if alias_analyzer.get("aliases"):
            defaults["column_aliases"] = " ".join(
                f"{k}:{v}" for k, v in alias_analyzer["aliases"].items()
            )

    def _apply_paper_aliases_flags(self, defaults: dict) -> None:
        if not self.paper_aliases:
            return
        parts = []
        for alias_name, paper_alias_data in self.paper_aliases.items():
            canonical = paper_alias_data["canonical"]
            offset = paper_alias_data.get("offset", 0)
            parts.append(
                f"{alias_name}:{canonical}:{offset}"
                if offset
                else f"{alias_name}:{canonical}"
            )
        defaults["paper_aliases"] = " ".join(parts)


def write_settings_file(settings: MergeSettings, output_path: Path) -> Path:
    settings_file_path = output_path / "settings.tablemerge.json"
    settings_file_path.write_text(
        json.dumps(dataclasses.asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf8",
    )
    return settings_file_path


def read_settings_file(output_path: Path) -> MergeSettings:
    settings_file_path = output_path / "settings.tablemerge.json"
    return MergeSettings.from_dict(
        json.loads(settings_file_path.read_text(encoding="utf8"))
    )
