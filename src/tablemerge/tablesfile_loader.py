import json
from pathlib import Path

from tablevalidate.schema import TablesFile, TableWithFragments
from tablemerge.fragment_transformer import FragmentTransformer
from tablemerge.fragments_compactor import FragmentsCompactor, NullFragmentsCompactor


class TablesFileLoader:
    def __init__(
        self,
        transformers: list[FragmentTransformer] = [],
        compactor: FragmentsCompactor = NullFragmentsCompactor(),
    ):
        self.transformers = transformers
        self.compactor = compactor

    @property
    def settings(self) -> dict:
        return {
            "transformers": {type(t).__name__: t.settings for t in self.transformers},
            "compactor": self.compactor.settings,
        }

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        tablesfile = self.transform_tablesfile(tablesfile)
        return self.compactor.compact(tablesfile)

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

    def transform_fragment(self, fragment):
        for transformer in self.transformers:
            fragment = transformer.transform_fragment(fragment)
        return fragment
