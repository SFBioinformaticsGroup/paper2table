import json
from pathlib import Path

from tablevalidate.schema import TablesFile, TableFragment, TableWithFragments
from tablemerge.fragment_transformer import FragmentTransformer
from tablemerge.tablesfile_transformer import (
    TablesfileTransformer,
    NullTablesfileTransformer,
)
from tablemerge.columns_aligner import LoadTimeColumnAligner
from tablemerge.analyzers import LoadTimeAnalyzer


class TablesFileLoader:
    def __init__(
        self,
        pretransformers: list[FragmentTransformer] = [],
        tablesfile_transformer: TablesfileTransformer = NullTablesfileTransformer(),
        analyzers: list[LoadTimeAnalyzer] = [],
        posttransformers: list[FragmentTransformer] = [],
    ):
        self.pretransformers = pretransformers
        self.tablesfile_transformer = tablesfile_transformer
        self.analyzers = analyzers
        self.posttransformers = posttransformers

    @property
    def settings(self) -> dict:
        return {
            "pretransformers": {
                type(t).__name__: t.settings for t in self.pretransformers
            },
            "tablesfile_transformer": self.tablesfile_transformer.settings,
            "analyzers": {type(a).__name__: a.settings for a in self.analyzers},
            "posttransformers": {
                type(t).__name__: t.settings for t in self.posttransformers
            },
        }

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        tablesfile = self.transform_tablesfile(tablesfile, self.pretransformers)
        tablesfile = self.tablesfile_transformer.transform(tablesfile)
        tablesfile = self.align_tablesfile(tablesfile)
        return self.transform_tablesfile(tablesfile, self.posttransformers)

    def transform_tablesfile(
        self, tablesfile: TablesFile, transformers: list[FragmentTransformer]
    ) -> TablesFile:
        if not transformers:
            return tablesfile
        return tablesfile.clone(
            tables=[
                TableWithFragments(
                    table_fragments=[
                        self.transform_fragment(fragment, transformers)
                        for fragment in table.get_table_fragments()
                    ]
                )
                for table in tablesfile.tables
            ]
        )

    def transform_fragment(
        self, fragment: TableFragment, transformers: list[FragmentTransformer]
    ) -> TableFragment:
        for transformer in transformers:
            fragment = transformer.transform_fragment(fragment)
        return fragment

    def align_tablesfile(self, tablesfile: TablesFile) -> TablesFile:
        return tablesfile.clone(
            tables=[
                TableWithFragments(
                    table_fragments=[
                        self.align_fragment(fragment)
                        for fragment in table.get_table_fragments()
                    ]
                )
                for table in tablesfile.tables
            ]
        )

    def align_fragment(self, fragment: TableFragment) -> TableFragment:
        aligner = LoadTimeColumnAligner(fragment, self.analyzers)
        if not aligner.mapping:
            return fragment
        return TableFragment(
            rows=[aligner.rename_row(r) for r in fragment.rows],
            page=fragment.page,
        )
