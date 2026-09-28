from dataclasses import dataclass

from app.domain.entities.member_health_data import PHQ9_ITEM_FIELDS


@dataclass(frozen=True)
class FormDefinition:
    """Domain value object representing a health form definition."""

    form_type: str
    fields: list[str]
    version: str = "1"


class FormRegistry:
    """Domain registry for health data forms and their field definitions."""

    def __init__(self, forms: list[FormDefinition] | None = None) -> None:
        if forms is None:
            forms = [
                FormDefinition(
                    form_type="biometrics",
                    fields=[
                        "biological_sex",
                        "height",
                        "weight",
                        "waist_circumference",
                        "neck_circumference",
                    ],
                ),
                FormDefinition(
                    form_type="sleep",
                    fields=[
                        "snoring",
                        "tired",
                        "observed_apnea",
                        "neck_circumference",
                    ],
                ),
                FormDefinition(
                    form_type="habits",
                    fields=[
                        "daily_physical_activity",
                        "fruits_vegetables",
                        "hypertension_medication",
                        "previous_high_glucose",
                        "family_diabetes",
                        "smoker",
                    ],
                ),
                FormDefinition(
                    form_type="metabolic",
                    fields=[
                        "triglycerides",
                        "total_cholesterol",
                        "hdl_cholesterol",
                        "systolic_blood_pressure",
                        "diastolic_blood_pressure",
                        "fasting_glucose",
                        "glucose_lowering_medication",
                    ],
                ),
                FormDefinition(
                    form_type="eoss",
                    fields=[
                        "eoss_physical_health_stage",
                        "eoss_mental_health_stage",
                        "eoss_functional_stage",
                    ],
                ),
                FormDefinition(
                    form_type="mood",
                    fields=list(PHQ9_ITEM_FIELDS),
                ),
                FormDefinition(
                    form_type="nordic_nmq",
                    fields=["nordic_nmq_data"],
                ),
                FormDefinition(
                    form_type="audit_c",
                    fields=[
                        "audit_c_frequency",
                        "audit_c_quantity",
                        "audit_c_heavy_drinking",
                    ],
                ),
                FormDefinition(
                    form_type="pss10",
                    fields=[f"pss10_q{i}" for i in range(1, 11)],
                ),
            ]
        self._forms: dict[str, FormDefinition] = {
            form.form_type: form for form in forms
        }

    def get_registered_form_types(self) -> list[str]:
        """Returns the list of all registered form type identifiers."""
        return list(self._forms.keys())

    def get_form_fields(self, form_type: str) -> list[str]:
        """Returns the field names belonging to the specified form type."""
        form = self._forms.get(form_type)
        return list(form.fields) if form else []

    def is_valid_form_type(self, form_type: str) -> bool:
        """Returns True if form_type is registered in the registry."""
        return form_type in self._forms

    def get_form_version(self, form_type: str) -> str:
        """Returns the version string of the specified form type, defaulting to '1'."""
        form = self._forms.get(form_type)
        return form.version if form else "1"

    def get_form_fields_map(self) -> dict[str, list[str]]:
        """Returns a dictionary mapping form_type to its list of fields."""
        return {form_type: list(form.fields) for form_type, form in self._forms.items()}
