"""Domain-level exceptions.

Services raise these instead of ``fastapi.HTTPException`` directly, so
the service layer stays framework-agnostic. ``app/main.py`` registers
exception handlers that translate them into HTTP responses.
"""


class NotFoundError(Exception):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: object) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id '{entity_id}' was not found.")


class UnsupportedMediaTypeError(Exception):
    """Raised when an uploaded file's type is not supported (e.g. not a PDF)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DocumentProcessingError(Exception):
    """Raised when a document was saved but could not be parsed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
