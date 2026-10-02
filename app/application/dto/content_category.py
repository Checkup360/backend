from dataclasses import dataclass


@dataclass(frozen=True)
class ContentCategoryDTO:
    """A health topic content can be tagged with, and whether it is enabled."""

    key: str
    label: str
    active: bool
