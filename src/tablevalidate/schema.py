from typing import List, Union, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

from utils.column_values import normalize_column_value
from utils.str import normalize_str


class ValueWithAgreement(BaseModel):
    value: str
    agreement_level: int


ColumnValue = Union[None, str, List[ValueWithAgreement]]


_SPECIAL_FIELDS = frozenset(("agreement_level_", "sources_", "row_"))


class Row(BaseModel):
    agreement_level_: Optional[int] = Field(None)
    sources_: Optional[List[str]] = Field(None)
    row_: Optional[int] = Field(None)

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def coerce_extra_columns(self) -> "Row":
        if self.__pydantic_extra__:
            for key, value in self.__pydantic_extra__.items():
                if isinstance(value, list):
                    self.__pydantic_extra__[key] = [
                        ValueWithAgreement.model_validate(v) if isinstance(v, dict) else v
                        for v in value
                    ]
        return self

    def __getitem__(self, item: str) -> ColumnValue:
        return self.__dict__[item]

    def get_columns(self) -> Dict[str, ColumnValue]:
        return {k: v for k, v in self if k not in _SPECIAL_FIELDS}

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
        return all(Row.is_empty_value(v) for v in self.get_columns().values())

    def get_agreement_level(self):
        return 1 if self.agreement_level_ is None else self.agreement_level_

    def normalize(
        self,
        row_agreement: bool = False,
    ):
        return Row(
            **{
                column: Row.normalize_value(value)
                for column, value in self.get_columns().items()
            },
            agreement_level_=(
                self.get_agreement_level() if row_agreement else self.agreement_level_
            ),
            sources_=self.sources_,
            row_=self.row_,
        )

    @staticmethod
    def column_names(rows: "List[Row]") -> "List[str]":
        return list(dict.fromkeys(col for row in rows for col in row.get_columns()))

    @staticmethod
    def is_empty_value(value: ColumnValue) -> bool:
        if value is None:
            return True

        if isinstance(value, str):
            return not normalize_column_value(value)

        return all(not normalize_column_value(v.value) for v in value)

    @staticmethod
    def normalize_value(value: ColumnValue) -> ColumnValue:
        if value is None:
            return None

        if isinstance(value, str):
            return normalize_column_value(value)

        return [
            ValueWithAgreement(
                value=normalize_column_value(value_with_agreement.value),
                agreement_level=value_with_agreement.agreement_level,
            )
            for value_with_agreement in value
        ]


class TableFragment(BaseModel):
    rows: List[Row]
    page: int

    def get_column_names(self) -> List[str]:
        return Row.column_names(self.rows)

    def columns_count(self) -> int:
        return len(self.get_column_names())

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)


class TableWithRows(BaseModel):
    rows: List[Row]
    page: int

    def get_table_fragments(self) -> List[TableFragment]:
        return [TableFragment(rows=self.rows, page=self.page)]

    def is_empty(self) -> bool:
        return all(row.is_empty() for row in self.rows)


class TableWithFragments(BaseModel):
    table_fragments: List[TableFragment]

    def get_table_fragments(self) -> List[TableFragment]:
        return list(self.table_fragments)

    def is_empty(self) -> bool:
        return all(fragment.is_empty() for fragment in self.table_fragments)


Table = Union[TableWithRows, TableWithFragments]


class Curation(BaseModel):
    curator: str
    description: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Metadata(BaseModel):
    filename: Optional[str]
    curations: Optional[List["Curation"]] = None

    model_config = ConfigDict(extra="allow")


Citation = Union[None, str, List[ValueWithAgreement]]


class TablesFile(BaseModel):
    tables: List[Table]
    citation: Citation
    metadata: Optional[Metadata] = None
    uuid: Optional[str] = None

    def clone(
        self,
        tables: Optional[List[Table]] = None,
        citation: Optional[Citation] = None,
        metadata: Optional[Metadata] = None,
        uuid: Optional[str] = None,
    ) -> "TablesFile":
        return TablesFile(
            tables=tables if tables is not None else self.tables,
            citation=citation if citation is not None else self.citation,
            metadata=metadata if metadata is not None else self.metadata,
            uuid=uuid if uuid is not None else self.uuid,
        )

    @staticmethod
    def normalize_citation(citation: Citation) -> Citation:
        if citation is None:
            return None
        if isinstance(citation, str):
            return normalize_str(citation)
        return [
            ValueWithAgreement(
                value=normalize_str(v.value), agreement_level=v.agreement_level
            )
            for v in citation
        ]
