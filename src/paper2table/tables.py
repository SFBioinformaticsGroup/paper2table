import os
from typing import Optional
from pandas import DataFrame


class Table:
    def __init__(self, page: int, dataframe: DataFrame, title: Optional[str] = None):
        self.page = page
        self.df = dataframe
        self.title = title

    def to_dict(self):
        return {
            "rows": self.df.to_dict(orient="records"),
            "page": self.page,
            **({"title": self.title} if self.title else {}),
        }


class Tables:
    def __init__(self, pdf_path: str, tables: list[Table]):
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.tables = tables

    def to_dict(self):
        return {
            "tables": [{"table_fragments": [table.to_dict()]} for table in self.tables],
            "citation": None,
            "metadata": {
                "filename": self.filename,
            },
        }
