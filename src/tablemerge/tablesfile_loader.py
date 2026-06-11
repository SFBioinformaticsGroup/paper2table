import json
from pathlib import Path

from tablevalidate.schema import TablesFile, TableWithFragments
from tablemerge.fragment_transformer import FragmentTransformer


class TablesFileLoader:
    def __init__(self, transformers: list[FragmentTransformer] = []):
        self.transformers = transformers

    @property
    def settings(self) -> dict:
        return {type(t).__name__: t.settings for t in self.transformers}

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        return self.transform_tablesfile(tablesfile)

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
