"""Domain service to determine active forms based on organization score weights."""

from app.domain.services.form_registry import FormDefinition, FormRegistry
from app.domain.services.risk_score_calculator import normalize_score_key

# Mapping from normalized score key to the form types required to evaluate that score
SCORE_REQUIRED_FORMS: dict[str, list[str]] = {
    "diabetes": ["biometrics", "habits"],
    "sleep_apnea": ["biometrics", "sleep"],
    "depression": ["mood"],
    "metabolic_syndrome": ["biometrics", "metabolic"],
    "eoss": ["eoss"],
    "cardiovascular": ["biometrics", "metabolic", "habits"],
}


class OrganizationFormPolicy:
    """
    Domain service evaluating which health data forms are active for an organization.
    A form is active if at least one enabled score (weight > 0) requires data from it.
    """

    def __init__(self, form_registry: FormRegistry | None = None) -> None:
        self._form_registry = form_registry or FormRegistry()

    def get_active_form_types(
        self, score_weights: dict[str, float] | None = None
    ) -> list[str]:
        """
        Returns list of form_type strings that are active under the given org score weights.
        If score_weights is None or empty, all registered forms are active by default.
        """
        all_registered = self._form_registry.get_registered_form_types()
        if not score_weights:
            return all_registered

        normalized_weights: dict[str, float] = {}
        for key, w in score_weights.items():
            norm_key = normalize_score_key(key)
            normalized_weights[norm_key] = float(w)

        active_form_types: set[str] = set()

        for score_key, form_types in SCORE_REQUIRED_FORMS.items():
            # If score_weights is provided, missing keys mean weight=0.0 (disabled)
            weight = normalized_weights.get(score_key, 0.0)
            if weight > 0:
                for ft in form_types:
                    if self._form_registry.is_valid_form_type(ft):
                        active_form_types.add(ft)

        # Retain order as registered in registry
        return [ft for ft in all_registered if ft in active_form_types]

    def get_active_form_definitions(
        self, score_weights: dict[str, float] | None = None
    ) -> list[FormDefinition]:
        """Returns list of active FormDefinition value objects."""
        active_types = set(self.get_active_form_types(score_weights))
        registered_types = self._form_registry.get_registered_form_types()

        result: list[FormDefinition] = []
        for ft in registered_types:
            if ft in active_types:
                fields = self._form_registry.get_form_fields(ft)
                result.append(FormDefinition(form_type=ft, fields=fields))
        return result
