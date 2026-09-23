"""Domain service to determine active forms based on organization health domain weights."""

from app.domain.entities.health_domain import HealthDomain
from app.domain.services.domain_dependency_matrix import DomainDependencyMatrix
from app.domain.services.form_registry import FormDefinition, FormRegistry

# Precise mapping between individual score keys and the forms they require
SCORE_REQUIRED_FORMS: dict[str, list[str]] = {
    "diabetes": ["biometrics", "habits"],
    "findrisc": ["biometrics", "habits"],
    "sleep_apnea": ["biometrics", "sleep"],
    "stop_bang": ["biometrics", "sleep"],
    "depression": ["biometrics", "mood"],
    "phq9": ["biometrics", "mood"],
    "metabolic_syndrome": ["biometrics", "metabolic"],
    "cardiovascular": ["biometrics", "habits", "metabolic"],
    "score2": ["biometrics", "habits", "metabolic"],
    "eoss": ["biometrics", "eoss"],
    "audit_c": ["biometrics", "audit_c"],
    "pss10": ["biometrics", "pss10"],
    "nordic_nmq": ["biometrics", "nordic_nmq"],
}

DOMAIN_REQUIRED_FORMS: dict[HealthDomain, list[str]] = {
    HealthDomain.CARDIOMETABOLIC: ["biometrics", "habits", "metabolic"],
    HealthDomain.FATIGUE_SLEEP: ["biometrics", "sleep", "nordic_nmq"],
    HealthDomain.MENTAL_HEALTH: ["biometrics", "mood", "eoss", "pss10"],
}


class OrganizationFormPolicy:
    """
    Domain service evaluating which health data forms are active for an organization.
    A form is active if required by at least one enabled score/health domain (weight > 0).
    """

    def __init__(
        self,
        form_registry: FormRegistry | None = None,
        dependency_matrix: DomainDependencyMatrix | None = None,
    ) -> None:
        self._form_registry = form_registry or FormRegistry()
        self._matrix = dependency_matrix or DomainDependencyMatrix()

    def get_active_form_types(
        self, score_weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Returns list of active form_type strings under configured score/domain weights.
        """
        all_registered = self._form_registry.get_registered_form_types()
        if score_weights is None:
            return all_registered

        active_form_types: set[str] = {"biometrics"}

        for key, weight in score_weights.items():
            if weight <= 0.0:
                continue

            normalized_key = key.lower().replace("-", "_").strip()

            if normalized_key in SCORE_REQUIRED_FORMS:
                for ft in SCORE_REQUIRED_FORMS[normalized_key]:
                    if self._form_registry.is_valid_form_type(ft):
                        active_form_types.add(ft)
            else:
                try:
                    matched_domain = HealthDomain(normalized_key)
                    for ft in DOMAIN_REQUIRED_FORMS.get(matched_domain, []):
                        if self._form_registry.is_valid_form_type(ft):
                            active_form_types.add(ft)
                except ValueError:
                    pass

        # These forms belong exclusively to a specific score.
        # If the score is explicitly disabled (or missing, thus weight 0),
        # they must not be shown, even if a broad HealthDomain was enabled.
        score_specific_forms = {"audit_c", "nordic_nmq", "pss10", "eoss"}
        final_form_types = set()

        normalized_weights = {
            k.lower().replace("-", "_").strip(): v for k, v in score_weights.items()
        }

        for ft in active_form_types:
            if ft in score_specific_forms and normalized_weights.get(ft, 0.0) <= 0.0:
                continue
            final_form_types.add(ft)

        return [ft for ft in all_registered if ft in final_form_types]

    def get_active_form_definitions(
        self, score_weights: dict[str, float] | None = None
    ) -> list[FormDefinition]:
        """Returns list of active FormDefinition value objects."""
        active_types = set(self.get_active_form_types(score_weights))
        registered_types = self._form_registry.get_registered_form_types()

        sleep_apnea_active = True
        if score_weights is not None:
            normalized_weights = {
                k.lower().replace("-", "_").strip(): v for k, v in score_weights.items()
            }
            sleep_weight = normalized_weights.get(
                "sleep_apnea", 0.0
            ) or normalized_weights.get("stop_bang", 0.0)
            fatigue_weight = normalized_weights.get(
                HealthDomain.FATIGUE_SLEEP.value, 0.0
            ) or normalized_weights.get("fatigue_sleep", 0.0)
            sleep_apnea_active = (sleep_weight > 0.0) or (fatigue_weight > 0.0)

        result: list[FormDefinition] = []
        for ft in registered_types:
            if ft in active_types:
                fields = self._form_registry.get_form_fields(ft)
                if ft == "biometrics" and not sleep_apnea_active:
                    fields = [f for f in fields if f != "neck_circumference"]
                result.append(FormDefinition(form_type=ft, fields=fields))
        return result
