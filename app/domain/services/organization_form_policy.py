"""Domain service to determine active forms based on organization health domain weights."""

from app.domain.entities.health_domain import InputFormModule
from app.domain.services.domain_dependency_matrix import DomainDependencyMatrix
from app.domain.services.form_registry import FormDefinition, FormRegistry

# Mapping between InputFormModule enum and legacy form_type strings
MODULE_TO_FORM_TYPES: dict[InputFormModule, list[str]] = {
    InputFormModule.BASE_BIOMETRICS: ["biometrics"],
    InputFormModule.LABORATORY_CLINIC: ["metabolic"],
    InputFormModule.LIFESTYLE_HABITS: ["habits", "audit_c"],
    InputFormModule.OPERATIONAL_FATIGUE: ["sleep", "nordic_nmq"],
    InputFormModule.PSYCHOLOGICAL_HEALTH: ["mood", "eoss", "pss10"],
}


class OrganizationFormPolicy:
    """
    Domain service evaluating which health data forms are active for an organization.
    A form is active if required by at least one enabled health domain (weight > 0).
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
        if not score_weights:
            return all_registered

        active_modules = self._matrix.get_active_form_modules(score_weights)

        active_form_types: set[str] = set()
        for module in active_modules:
            for ft in MODULE_TO_FORM_TYPES.get(module, []):
                if self._form_registry.is_valid_form_type(ft):
                    active_form_types.add(ft)

        all_registered = self._form_registry.get_registered_form_types()
        return [ft for ft in all_registered if ft in active_form_types]

    def get_active_form_definitions(
        self, score_weights: dict[str, float] | None = None
    ) -> list[FormDefinition]:
        """Returns list of active FormDefinition value objects."""
        active_modules = self._matrix.get_active_form_modules(score_weights)
        active_types = set(self.get_active_form_types(score_weights))
        registered_types = self._form_registry.get_registered_form_types()

        result: list[FormDefinition] = []
        for ft in registered_types:
            if ft in active_types:
                fields = self._form_registry.get_form_fields(ft)
                if ft == "biometrics":
                    if InputFormModule.OPERATIONAL_FATIGUE not in active_modules:
                        fields = [f for f in fields if f != "neck_circumference"]
                result.append(FormDefinition(form_type=ft, fields=fields))
        return result
