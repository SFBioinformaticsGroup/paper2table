from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from utils.jsonc import load_jsonc


class NormalizeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interactive: bool = True


class ExtractRun(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    reader: str = "pdfplumber"
    model: str | None = None
    model_sleep: int | None = None
    verbose: bool = False
    hybrid: bool = False
    override_mappings: bool = False
    schema_: str | None = Field(None, alias="schema")
    column_hints: str | None = None
    column_hints_path: str | None = None
    split_pages: int | None = None
    quiet: bool = False
    id: str | None = None


class ExtractConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    runs: list[ExtractRun]
    page_ranges: dict[str, str] | None = None
    stats: bool = False
    validate_: bool = Field(False, alias="validate")
    export: list[str] = []
    override: bool = False


class MergeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    agreement_method: str = "simple-count"
    filter_title_rows: bool = True
    remove_header_rows: bool = False
    jaccard_column_alignment: bool = False
    column_alignment_threshold: float = 0.5
    row_similarity_threshold: float = 0.6
    column_name_semantic_alignment: bool = False
    column_value_semantic_alignment: bool = False
    semantic_language: str = "en"
    column_aliases: str | None = None
    column_aliases_path: str | None = None
    column_hints: str | None = None
    column_hints_path: str | None = None
    hints_column_alignment: str | None = None
    paper_aliases: str | None = None
    paper_aliases_path: str | None = None
    fix_reversed_column_values: bool = False
    strip_leading_row_numbers: bool = False
    normalize_punctuation: bool = False
    split_conjunction_columns: bool = False
    transform_tablesfile: str | None = None
    filter_schema_columns: bool = False
    order_schema_columns: bool = False
    coerce_schema_column_types: bool = False
    filter_semantic_columns: bool = False
    drop_empty_columns: bool = True
    drop_empty_tables: bool = True
    validate_: bool = Field(False, alias="validate")
    stats: bool = False
    export: list[str] = []
    override: bool = False


class GatherConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    convergence: str = "none"
    key_columns: list[str] | None = None
    filter_schema_columns: bool = False
    order_schema_columns: bool = False
    coerce_schema_column_types: bool = False
    filter_semantic_columns: bool = False
    drop_empty_columns: bool = True
    drop_empty_tables: bool = True
    stats: bool = False
    export: list[str] = []
    override: bool = False


class ReadmeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override: bool = False


class Pipeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    working_path: str
    pretty: bool = False
    normalize: NormalizeConfig | None = None
    extract: ExtractConfig | None = None
    merge: MergeConfig | None = None
    gather: GatherConfig | None = None
    readme: ReadmeConfig | None = None


def load_pipeline(path: str) -> Pipeline:
    return Pipeline.model_validate(load_jsonc(Path(path)))
