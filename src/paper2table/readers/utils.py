from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent

from paper2table.readers.errors import ModelUnavailableError
from utils.column_names import normalize_column_name

type Row = list[str | None]

def first_row_is_table_header(rows: list[Row], column_names_hints: list[str]):
    return (
        rows
        and column_names_hints
        and any(normalize_column_name(key) in column_names_hints for key in rows[0])
    )


def is_model_unavailable(e: BaseException) -> bool:
    try:
        from google.genai.errors import ServerError
        if isinstance(e, ServerError) and (
            e.code == 503 or "currently experiencing high demand" in str(e.message)
        ):
            return True
    except ImportError:
        pass
    error_text = str(e).lower()
    return "503" in error_text and (
        "unavailable" in error_text or "high demand" in error_text
    )

def run_agent_on_pdf[T](agent: Agent[None, T], pdf_path: Path):
    try:
        return agent.run_sync(
            [
                BinaryContent(
                    data=pdf_path.read_bytes(), media_type="application/pdf"
                ),
            ]
        ).output
    except BaseException as e:
        if is_model_unavailable(e):
            raise ModelUnavailableError(str(e)) from e
        raise