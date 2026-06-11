import json
from pathlib import Path

from tablevalidate.schema import TablesFile, TableFragment, TableWithFragments
from tablemerge.fragment_transformer import FragmentTransformer
from tablemerge.fragments_compactor import FragmentsCompactor, NullFragmentsCompactor
from tablemerge.columns_aligner import LoadTimeColumnAligner
from tablemerge.analyzers import LoadTimeAnalyzer


class TablesFileLoader:
    def __init__(
        self,
        transformers: list[FragmentTransformer] = [],
        compactor: FragmentsCompactor = NullFragmentsCompactor(),
        analyzers: list[LoadTimeAnalyzer] = [],
    ):
        self.transformers = transformers
        self.compactor = compactor
        self.analyzers = analyzers

    @property
    def settings(self) -> dict:
        return {
            "transformers": {type(t).__name__: t.settings for t in self.transformers},
            "compactor": self.compactor.settings,
            "analyzers": {
                type(a).__name__: a.settings for a in self.analyzers
            },
        }

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        tablesfile = self.transform_tablesfile(tablesfile)
        tablesfile = self.compactor.compact(tablesfile)
        return self.align_tablesfile(tablesfile)

    def transform_tablesfile(self, tablesfile: TablesFile) -> TablesFile:
        return TablesFile(
            tables=[
                TableWithFragments(
                    table_fragments=[
                        self.transform_fragment(fragment)
                        for fragment in table.get_table_fragments()
                    ]
                )
                for table in tablesfile.tables
            ],
            citation=tablesfile.citation,
            metadata=tablesfile.metadata,
            uuid=tablesfile.uuid,
        )

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        for transformer in self.transformers:
            fragment = transformer.transform_fragment(fragment)
        return fragment

    def align_tablesfile(self, tablesfile: TablesFile) -> TablesFile:
        return TablesFile(
            tables=[
                TableWithFragments(
                    table_fragments=[
                        self.align_fragment(fragment)
                        for fragment in table.get_table_fragments()
                    ]
                )
                for table in tablesfile.tables
            ],
            citation=tablesfile.citation,
            metadata=tablesfile.metadata,
            uuid=tablesfile.uuid,
        )

    def align_fragment(self, fragment: TableFragment) -> TableFragment:
        aligner = LoadTimeColumnAligner(fragment, self.analyzers)
        if not aligner.mapping:
            return fragment
        return TableFragment(
            rows=[aligner.rename_row(r) for r in fragment.rows],
            page=fragment.page,
        )
