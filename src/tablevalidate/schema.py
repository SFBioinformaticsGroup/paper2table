from typing import List, Union, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from utils.rows import is_empty_value


class ValueWithAgreement(BaseModel):
    value: str
    agreement_level: int


ColumnValue = Union[str, List[ValueWithAgreement]]


class Row(BaseModel):
    agreement_level_: Optional[int] = Field(None)
    sources_: Optional[List[str]] = Field(None)

    model_config = ConfigDict(extra="allow")

    def __getitem__(self, item: str) -> ColumnValue:
        return self.__dict__[item]

    def get_columns(self) -> Dict[str, ColumnValue]:
        return {k: v for k, v in self if k not in ("agreement_level_", "sources_")}

    @staticmethod
    def is_semantic_column(name: str) -> bool:
        try:
            float(name)
            return False
        except ValueError:
            return True

    def get_semantic_columns(self) -> Dict[str, ColumnValue]:
        return {
            k: v for k, v in self.get_columns().items() if self.is_semantic_column(k)
        }

    def is_empty(self) -> bool:
        return all(is_empty_value(v) for v in self.get_columns().values())

    def get_agreement_level(self):
        return 1 if self.agreement_level_ is None else self.agreement_level_

    @staticmethod
    def column_names(rows: "List[Row]") -> "List[str]":
        return list(dict.fromkeys(col for row in rows for col in row.get_columns()))


class TableFragment(BaseModel):
    rows: List[Row]
    page: int

    def get_column_names(self) -> List[str]:
        return Row.column_names(self.rows)


class TableWithRows(BaseModel):
    rows: List[Row]
    page: int

    def get_table_fragments(self) -> List[TableFragment]:
        return [TableFragment(rows=self.rows, page=self.page)]


class TableWithFragments(BaseModel):
    table_fragments: List[TableFragment]

    def get_table_fragments(self) -> List[TableFragment]:
        return list(self.table_fragments)


Table = Union[TableWithRows, TableWithFragments]


class Metadata(BaseModel):
    filename: Optional[str]

    model_config = ConfigDict(extra="allow")


Citation = Union[Optional[str], List[ValueWithAgreement]]


class TablesFile(BaseModel):
    tables: List[Table]
    citation: Citation
    metadata: Optional[Metadata] = None
    uuid: Optional[str] = None
