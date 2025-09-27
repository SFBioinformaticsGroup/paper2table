
import os
from pandas import DataFrame

class Table:
    def __init__(self, index: int, page: int, dataframe: DataFrame):
        self.index = index
        self.page = page
        self.df = dataframe

    def to_dict(self):
        return {
            "rows": self.df.to_dict(orient="records"),
            "metadata": {
                "page": self.page,
                "index": self.index,
            },
        }


class Tables:
    def __init__(self, pdf_path: str, tables: list[Table], citation=None):
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.tables = tables
        self.citation = citation

    def to_dict(self):
        return {
            "tables": [table.to_dict() for table in self.tables],
            "citation": self.citation,
            "metadata": {
                "filename": self.filename,
            },
        }