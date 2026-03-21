import os
from typing import Optional
from pandas import DataFrame, Series


class DataFrameTableReader:
    def __init__(
        self, page: int, dataframe: DataFrame | Series, title: Optional[str] = None
    ):
        self.page = page
        self.df = dataframe if isinstance(dataframe, DataFrame) else DataFrame()
        self.title = title

    @property
    def rows(self):
        return self.df.to_dict(orient="records")

    def to_dict(self):
        return {
            "rows": self.rows,
            "page": self.page,
            **({"title": self.title} if self.title else {}),
        }


class DataFrameTablesReader:
    """
    A TablesReader
    that is designed to work with a pandas dataframe
    as a backend
    """

    def __init__(
        self,
        pdf_path: str,
        tables: list[DataFrameTableReader],
        citation: Optional[str] = None,
    ):
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.tables = tables
        self.citation = citation

    def to_dict(self):
        return {
            "tables": [{"table_fragments": [table.to_dict()]} for table in self.tables],
            "citation": self.citation,
            "metadata": {
                "filename": self.filename,
            },
        }
