"""Domain exceptions mapped to transport errors at the edges."""

from uuid import UUID


class DomainError(Exception):
    """Base class for business rule violations."""


class InvalidItemError(DomainError):
    """Raised when an item breaks an invariant."""


class ItemNotFoundError(DomainError):
    """Raised when an item does not exist (or belongs to someone else)."""

    def __init__(self, item_id: UUID) -> None:
        super().__init__(f"Item {item_id} not found")
        self.item_id = item_id


class AuthenticationError(DomainError):
    """Raised when the caller's credentials are missing or invalid (HTTP 401)."""


class PermissionDeniedError(DomainError):
    """Raised when an authenticated caller lacks a required permission (HTTP 403)."""

    def __init__(self, missing_scopes: frozenset[str]) -> None:
        super().__init__(f"Missing required scope(s): {' '.join(sorted(missing_scopes))}")
        self.missing_scopes = missing_scopes
