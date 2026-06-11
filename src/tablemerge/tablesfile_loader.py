import json
from pathlib import Path

from tablevalidate.schema import TablesFile, TableWithFragments
from tablemerge.merge import filter_title_rows
from tablemerge.fragment_transformer import NullFragmentTransformer, FragmentTransformer


class TablesFileLoader:
    def __init__(
        self,
        transformer: FragmentTransformer = NullFragmentTransformer(),
        filter_title_rows: bool = True,
    ):
        self.transformer = transformer
        self.filter_title_rows = filter_title_rows

    @property
    def settings(self) -> dict:
        return {
            "fragment_transformer": self.transformer.settings,
            "filter_title_rows": self.filter_title_rows,
        }

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        tablesfile = self.transform_tablesfile(tablesfile)
        if self.filter_title_rows:
            tablesfile = filter_title_rows(tablesfile)
        return tablesfile

    def transform_tablesfile(self, tablesfile: TablesFile):
        return TablesFile(
            tables=[
                TableWithFragments(
                    table_fragments=[
                        self.transformer.transform_fragment(fragment)
                        for fragment in table.get_table_fragments()
                    ]
                )
                for table in tablesfile.tables
            ],
            citation=tablesfile.citation,
        )
