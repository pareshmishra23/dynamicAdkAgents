from __future__ import annotations


class RegistryServiceError(Exception):
    """Base error for the registry service."""


class NotFoundError(RegistryServiceError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} not found: {resource_id}")
        self.resource = resource
        self.resource_id = resource_id


class DuplicateError(RegistryServiceError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(f"{resource} already registered: {resource_id}")
        self.resource = resource
        self.resource_id = resource_id