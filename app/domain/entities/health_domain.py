"""Domain entities and value objects for health domains and dynamic input modules."""

from dataclasses import dataclass
from enum import Enum


class HealthDomain(str, Enum):
    """Output health domains configured by the employer."""

    CARDIOMETABOLIC = "cardiometabolic"
    FATIGUE_SLEEP = "fatigue_sleep"
    MENTAL_HEALTH = "mental_health"


class InputFormModule(str, Enum):
    """Input questionnaire form modules rendered for employees."""

    BASE_BIOMETRICS = "base_biometrics"
    LABORATORY_CLINIC = "laboratory_clinic"
    LIFESTYLE_HABITS = "lifestyle_habits"
    OPERATIONAL_FATIGUE = "operational_fatigue"
    PSYCHOLOGICAL_HEALTH = "psychological_health"


@dataclass(frozen=True)
class HealthDomainConfig:
    """Domain configuration for an active health domain and its employer weight."""

    domain: HealthDomain
    is_active: bool = True
    weight: float = 0.0

    def __post_init__(self) -> None:
        if self.weight < 0.0 or self.weight > 100.0:
            raise ValueError("Domain weight must be between 0.0 and 100.0")
