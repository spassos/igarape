"""Domain exceptions mapped to transport errors at the edges."""

from uuid import UUID


class DomainError(Exception):
    """Base class for business rule violations."""


class InvalidItemError(DomainError):
    """Raised when an item breaks an invariant."""


class ItemNotFoundError(DomainError):
    """Raised when an item does not exist."""

    def __init__(self, item_id: UUID) -> None:
        super().__init__(f"Item {item_id} not found")
        self.item_id = item_id
