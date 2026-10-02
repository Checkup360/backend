from dataclasses import dataclass


@dataclass(frozen=True)
class HealthTopic:
    """
    Health topic informed by a risk score, as declared by the scoring engine.

    ``key`` is the stable identifier organizations weight and enable, and the
    tag content is categorized with. ``label`` is its readable name.
    """

    key: str
    label: str

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.label.strip():
            raise ValueError("HealthTopic key and label must not be empty")
