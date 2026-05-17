from ..tables_reader import TablesReader

class PartialProcessingError(ValueError):
    def __init__(
        self, page_num: int, partial_result: TablesReader, cause: BaseException
    ):
        self.page_num = page_num
        self.partial_result = partial_result
        super().__init__(f"Failed to process page {page_num}: {cause}")
