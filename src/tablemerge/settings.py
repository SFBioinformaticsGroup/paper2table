from argparse import Namespace
import dataclasses
import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

from utils.read_path import read_path
from utils.column_schema import ColumnSchema


@dataclass
class MergeSettings:
    agreement_method: str = "simple-count"
    coerce_schema_column_types: bool = False
    column_aliases: Optional[str] = None
    column_alignment_threshold: float = 0.5
    column_name_semantic_alignment: bool = False
    column_names_hints: Optional[str] = None
    column_value_semantic_alignment: bool = False
    drop_empty_columns: bool = True
    drop_empty_tables: bool = True
    filter_schema_columns: bool = False
    filter_title_rows: bool = True
    fix_reversed_column_values: bool = False
    hints_column_alignment: bool = False
    jaccard_column_alignment: bool = False
    normalize_punctuation: bool = False
    only_semantic_columns: bool = False
    order_schema_columns: bool = False
    paper_aliases: Optional[str] = None
    pretty: bool = False
    remove_header_rows: bool = False
    schema: Optional[str] = None
    semantic_language: str = "en"
    split_conjunction_columns: bool = False
    strip_leading_row_numbers: bool = False
    transform_tablesfile: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MergeSettings":
        return cls(**{k: v for k, v in data.items() if k in MERGE_SETTINGS_FIELDS})

    @classmethod
    def from_args(cls, args: Namespace) -> "MergeSettings":
        return cls.from_dict(
            {
                **args.__dict__,
                "column_aliases": read_path(
                    args.column_aliases_path, inline=args.column_aliases
                ),
                "paper_aliases": read_path(
                    args.paper_aliases_path, inline=args.paper_aliases
                ),
                "column_names_hints": read_path(
                    args.column_names_hints_path, inline=args.column_names_hints
                ),
                "schema": read_path(args.schema_path, inline=args.schema),
            }
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def write_file(self, output_path: Path) -> Path:
        settings_file_path = MergeSettings.settings_path(output_path)
        settings_file_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf8",
        )
        return settings_file_path

    @classmethod
    def read_file(cls, output_path: Path) -> "MergeSettings":
        settings_file_path = cls.settings_path(output_path)
        return cls.from_dict(json.loads(settings_file_path.read_text(encoding="utf8")))

    @staticmethod
    def settings_path(output_path: Path):
        return output_path / "settings.tablemerge.json"


MERGE_SETTINGS_FIELDS = [field.name for field in fields(MergeSettings)]
