import shutil
import subprocess
import sys
from pathlib import Path

from .pipeline import (
    ExtractConfig,
    ExtractRun,
    GatherConfig,
    MergeConfig,
    NormalizeConfig,
    Pipeline,
)


class PipelineError(Exception):
    pass


def run_subprocess(
    args: list[str], step_name: str, capture_output: bool = False
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [sys.executable, "-m", *args],
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except subprocess.CalledProcessError as error:
        raise PipelineError(
            f"{step_name} failed with exit code {error.returncode}"
        ) from error


def collect_pdfs(paths: list[str]) -> list[str]:
    files = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            files.extend(str(f) for f in sorted(p.glob("*.pdf")))
        elif p.is_file():
            files.append(str(p))
    return files


def run_stats(input_dir: Path, step_name: str) -> None:
    result = run_subprocess(
        ["tablestats", str(input_dir)], step_name=step_name, capture_output=True
    )
    (input_dir / "stats.txt").write_text(result.stdout, encoding="utf-8")


def run_validate(table_files: list[Path], step_name: str) -> None:
    run_subprocess(
        ["tablevalidate", *[str(p) for p in table_files]], step_name=step_name
    )


def run_export(input_dir: Path, export: list[str], step_name: str) -> None:
    if "csv" in export:
        csv_dir = input_dir / "csv"
        csv_dir.mkdir(exist_ok=True)
        run_subprocess(
            ["table2csv", str(input_dir), "-o", str(csv_dir)],
            step_name=f"{step_name} csv",
        )
    if "html" in export:
        run_subprocess(
            [
                "table2html",
                str(input_dir),
                "--out",
                str(input_dir / "viewer.html"),
                "--quiet",
            ],
            step_name=f"{step_name} html",
        )


def run_normalize(
    config: NormalizeConfig, output_path: Path, input_paths: list[str]
) -> list[str]:
    if config.inplace:
        papers_dir = output_path / "papers"
        papers_dir.mkdir(parents=True, exist_ok=True)
        for src in collect_pdfs(input_paths):
            shutil.copy2(src, papers_dir / Path(src).name)
        filenorm_files = sorted(str(f) for f in papers_dir.glob("*.pdf"))
    else:
        filenorm_files = collect_pdfs(input_paths)

    args = ["filenorm"]
    if not config.interactive:
        args += ["-y", "-q"]
    args += filenorm_files
    print("[pipeline] normalize", file=sys.stderr, flush=True)
    run_subprocess(args, step_name="normalize")

    if config.inplace:
        return sorted(str(f) for f in (output_path / "papers").glob("*.pdf"))
    return collect_pdfs(input_paths)


def find_new_uuid_dir(tables_dir: Path, before: set[Path]) -> Path:
    after = set(d for d in tables_dir.iterdir() if d.is_dir())
    new_dirs = after - before
    if len(new_dirs) != 1:
        raise PipelineError(
            f"Expected exactly one new directory after extract run, found: {new_dirs}"
        )
    return new_dirs.pop()


def build_extract_args(
    run: ExtractRun, schema_path: str | None, output_path: Path, paper_files: list[str]
) -> list[str]:
    args = [
        "paper2table",
        "-t",
        "-o",
        str(output_path / "tables"),
        "-r",
        run.reader,
    ]
    if run.model:
        args += ["-m", run.model]
    if run.model_sleep is not None:
        args += ["-z", str(run.model_sleep)]
    if run.hybrid:
        args += ["-H"]
    if run.force_mapping_generation:  # TODO ensure or document where mappings go
        args += ["-F"]
    if run.schema_:
        args += ["-s", run.schema_]
    elif schema_path:
        args += ["-p", schema_path]
    if run.column_names_hints_path:
        args += ["-c", run.column_names_hints_path]
    if run.split_pages is not None:
        args += ["--split-pages", str(run.split_pages)]
    if run.verbose:
        args += ["-vv"]  # TODO make verbosity global arg
    if run.quiet:
        args += ["-q"]
    args += paper_files
    return args


def run_extract(
    config: ExtractConfig,
    output_path: Path,
    paper_files: list[str],
    schema_path: str | None,
) -> None:
    tables_dir = output_path / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    for i, run in enumerate(config.runs):
        before = set(d for d in tables_dir.iterdir() if d.is_dir())
        print(f"[pipeline] extract (run {i + 1}/{len(config.runs)})", file=sys.stderr, flush=True)
        run_subprocess(
            build_extract_args(run, schema_path, output_path, paper_files),
            step_name=f"extract run {i + 1}",
        )
        uuid_dir = find_new_uuid_dir(tables_dir, before)

        if config.stats:
            run_stats(uuid_dir, step_name=f"extract run {i + 1} stats")
        if config.validate_:
            table_files = sorted(uuid_dir.glob("*.tables.json"))
            if table_files:
                run_validate(table_files, step_name=f"extract run {i + 1} validate")
        if config.export:
            run_export(uuid_dir, config.export, step_name=f"extract run {i + 1} export")


def build_merge_args(
    config: MergeConfig, output_path: Path, schema_path: str | None
) -> list[str]:
    tables_dir = output_path / "tables"
    merges_dir = output_path / "merges"
    input_dirs = sorted(str(d) for d in tables_dir.iterdir() if d.is_dir())

    args = [
        "tablemerge",
        "-o",
        str(merges_dir),
        "--agreement-method",
        config.agreement_method,
    ]

    if schema_path:
        args += ["-p", schema_path]
    if not config.filter_title_rows:
        args += ["--no-filter-title-rows"]
    if config.remove_header_rows:
        args += ["--remove-header-rows"]
    if config.jaccard_column_alignment:
        args += ["--jaccard-column-alignment"]
    if config.column_alignment_threshold != 0.5:
        args += ["--column-alignment-threshold", str(config.column_alignment_threshold)]
    if config.column_name_semantic_alignment:
        args += ["--column-name-semantic-alignment"]
    if config.column_value_semantic_alignment:
        args += ["--column-value-semantic-alignment"]
    if config.semantic_language != "en":
        args += ["--semantic-language", config.semantic_language]
    if config.column_aliases:
        args += ["--column-aliases", config.column_aliases]
    if config.column_aliases_path:
        args += ["--column-aliases-path", config.column_aliases_path]
    if config.column_names_hints:
        args += ["--column-names-hints", config.column_names_hints]
    if config.column_names_hints_path:
        args += ["--column-names-hints-path", config.column_names_hints_path]
    if config.hints_column_alignment:
        args += ["--hints-column-alignment", config.hints_column_alignment]
    if config.paper_aliases:
        args += ["--paper-aliases", config.paper_aliases]
    if config.paper_aliases_path:
        args += ["--paper-aliases-path", config.paper_aliases_path]
    if config.fix_reversed_column_values:
        args += ["--fix-reversed-column-values"]
    if config.strip_leading_row_numbers:
        args += ["--strip-leading-row-numbers"]
    if config.normalize_punctuation:
        args += ["--normalize-punctuation"]
    if config.split_conjunction_columns:
        args += ["--split-conjunction-columns"]
    if config.transform_tablesfile:
        args += ["--transform-tablesfile", config.transform_tablesfile]
    if config.filter_schema_columns:
        args += ["--filter-schema-columns"]
    if config.order_schema_columns:
        args += ["--order-schema-columns"]
    if config.coerce_schema_column_types:
        args += ["--coerce-schema-column-types"]
    if config.filter_semantic_columns:
        args += ["--filter-semantic-columns"]
    if not config.drop_empty_columns:
        args += ["--no-drop-empty-columns"]
    if not config.drop_empty_tables:
        args += ["--no-drop-empty-tables"]

    args += input_dirs
    return args


def run_merge(config: MergeConfig, output_path: Path, schema_path: str | None) -> None:
    merges_dir = output_path / "merges"
    merges_dir.mkdir(parents=True, exist_ok=True)

    print("[pipeline] merge", file=sys.stderr, flush=True)
    run_subprocess(
        build_merge_args(config, output_path, schema_path), step_name="merge"
    )

    if config.stats:
        run_stats(merges_dir, step_name="merge stats")
    if config.validate_:
        table_files = sorted(merges_dir.glob("*.tables.json"))
        if table_files:
            run_validate(table_files, step_name="merge validate")
    if config.export:
        run_export(merges_dir, config.export, step_name="merge export")


def build_gather_args(
    config: GatherConfig, output_path: Path, schema_path: str | None
) -> list[str]:
    merges_dir = output_path / "merges"
    gathers_dir = output_path / "gathers"

    args = ["tablegather", "-o", str(gathers_dir), "--convergence", config.convergence]

    if schema_path:
        args += ["-p", schema_path]
    if config.key_columns:
        args += ["--key-columns", *config.key_columns]
    if config.filter_schema_columns:
        args += ["--filter-schema-columns"]
    if config.order_schema_columns:
        args += ["--order-schema-columns"]
    if config.coerce_schema_column_types:
        args += ["--coerce-schema-column-types"]
    if config.filter_semantic_columns:
        args += ["--filter-semantic-columns"]
    if not config.drop_empty_columns:
        args += ["--no-drop-empty-columns"]
    if not config.drop_empty_tables:
        args += ["--no-drop-empty-tables"]

    args += [str(merges_dir)]
    return args


def run_gather(
    config: GatherConfig, output_path: Path, schema_path: str | None
) -> None:
    gathers_dir = output_path / "gathers"
    gathers_dir.mkdir(parents=True, exist_ok=True)

    print("[pipeline] gather", file=sys.stderr, flush=True)
    run_subprocess(
        build_gather_args(config, output_path, schema_path), step_name="gather"
    )

    if config.stats:
        run_stats(gathers_dir, step_name="gather stats")
    if config.export:
        run_export(gathers_dir, config.export, step_name="gather export")


def run_pipeline(pipeline: Pipeline) -> None:
    output_path = Path(pipeline.output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    if pipeline.normalize:
        paper_files = run_normalize(
            pipeline.normalize, output_path, pipeline.input_paths
        )
    else:
        paper_files = collect_pdfs(pipeline.input_paths)

    if pipeline.extract:
        run_extract(pipeline.extract, output_path, paper_files, pipeline.schema_path)

    # TODO validate that: there is at least one extract.
    # Also, if there is more than one extract and gather is present,
    # that there must be one merge
    if pipeline.merge:
        run_merge(pipeline.merge, output_path, pipeline.schema_path)

    if pipeline.gather:
        run_gather(pipeline.gather, output_path, pipeline.schema_path)
