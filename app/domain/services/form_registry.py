from dataclasses import dataclass


@dataclass(frozen=True)
class FormDefinition:
    """Domain value object representing a health form definition."""

    form_type: str
    fields: list[str]


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
                    ],
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

    def get_form_fields_map(self) -> dict[str, list[str]]:
        """Returns a dictionary mapping form_type to its list of fields."""
        return {form_type: list(form.fields) for form_type, form in self._forms.items()}
