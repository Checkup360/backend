"""Domain service computing active input form modules required by active health domains."""

from typing import Mapping

from app.domain.entities.health_domain import HealthDomain, InputFormModule

# Mapping from Output Health Domains to their required Input Form Modules
DOMAIN_REQUIRED_INPUT_MODULES: dict[HealthDomain, list[InputFormModule]] = {
    HealthDomain.CARDIOMETABOLIC: [
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.LABORATORY_CLINIC,
        InputFormModule.LIFESTYLE_HABITS,
    ],
    HealthDomain.FATIGUE_SLEEP: [
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.OPERATIONAL_FATIGUE,
    ],
    HealthDomain.MENTAL_HEALTH: [
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.PSYCHOLOGICAL_HEALTH,
    ],
}

# Legacy score key mapping for backward compatibility
LEGACY_SCORE_TO_HEALTH_DOMAIN: dict[str, HealthDomain] = {
    "diabetes": HealthDomain.CARDIOMETABOLIC,
    "metabolic_syndrome": HealthDomain.CARDIOMETABOLIC,
    "cardiovascular": HealthDomain.CARDIOMETABOLIC,
    "score2": HealthDomain.CARDIOMETABOLIC,
    "findrisc": HealthDomain.CARDIOMETABOLIC,
    "sleep_apnea": HealthDomain.FATIGUE_SLEEP,
    "stop_bang": HealthDomain.FATIGUE_SLEEP,
    "depression": HealthDomain.MENTAL_HEALTH,
    "phq9": HealthDomain.MENTAL_HEALTH,
    "eoss": HealthDomain.MENTAL_HEALTH,
}


class DomainDependencyMatrix:
    """
    Domain service evaluating the intersection of required input form modules.
    Base Biometrics is immutable and always required.
    """

    def get_active_form_modules(
        self, domain_weights: Mapping[str, float] | None = None
    ) -> set[InputFormModule]:
        """
        Returns the set of active InputFormModule enums given configured domain weights.
        Base Biometrics is always included.
        If domain_weights is None or empty, all input modules are active.
        """
        active_modules: set[InputFormModule] = {InputFormModule.BASE_BIOMETRICS}

        if domain_weights is None:
            # By default when unconfigured, all modules are active
            return {module for module in InputFormModule}

        for key, weight in domain_weights.items():
            if weight <= 0.0:
                continue

            normalized_key = key.lower().replace("-", "_").strip()
            matched_domain: HealthDomain | None = None

            # Try matching enum value directly
            try:
                matched_domain = HealthDomain(normalized_key)
            except ValueError:
                # Try matching legacy key
                matched_domain = LEGACY_SCORE_TO_HEALTH_DOMAIN.get(normalized_key)

            if matched_domain and matched_domain in DOMAIN_REQUIRED_INPUT_MODULES:
                for module in DOMAIN_REQUIRED_INPUT_MODULES[matched_domain]:
                    active_modules.add(module)

        return active_modules
