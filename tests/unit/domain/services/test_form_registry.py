"""Unit tests for FormRegistry and FormDefinition versioning."""

from app.domain.services.form_registry import FormDefinition, FormRegistry


def test_form_definition_default_version():
    form = FormDefinition(form_type="test_form", fields=["field1", "field2"])
    assert form.form_type == "test_form"
    assert form.fields == ["field1", "field2"]
    assert form.version == "1"


def test_form_definition_custom_version():
    form = FormDefinition(form_type="test_form", fields=["field1"], version="2.1")
    assert form.version == "2.1"


def test_form_registry_default_registered_forms_have_version_1():
    registry = FormRegistry()
    form_types = registry.get_registered_form_types()
    assert len(form_types) == 9

    for form_type in form_types:
        assert registry.get_form_version(form_type) == "1"


def test_form_registry_unknown_form_type_defaults_to_version_1():
    registry = FormRegistry()
    assert registry.get_form_version("non_existent_form") == "1"


def test_form_registry_custom_form_definitions():
    custom_forms = [
        FormDefinition(
            form_type="biometrics", fields=["height", "weight"], version="2"
        ),
        FormDefinition(form_type="mood", fields=["feeling_down"], version="3.0"),
    ]
    registry = FormRegistry(forms=custom_forms)
    assert registry.get_form_version("biometrics") == "2"
    assert registry.get_form_version("mood") == "3.0"
    assert registry.get_form_fields("biometrics") == ["height", "weight"]


def test_metabolic_form_includes_statins_and_lab_study_date():
    fields = FormRegistry().get_form_fields("metabolic")
    assert "statins" in fields
    assert "lab_study_date" in fields


def test_every_member_form_update_field_belongs_to_a_registered_form():
    from app.presentation.api.request_models.member_forms import MemberFormUpdate

    registry = FormRegistry()
    registered_fields = {
        field
        for form_type in registry.get_registered_form_types()
        for field in registry.get_form_fields(form_type)
    }
    unregistered = set(MemberFormUpdate.model_fields) - registered_fields
    assert unregistered == set()


def test_every_registered_form_field_can_be_stored_in_an_assessment_submission():
    import dataclasses

    from app.domain.entities.assessment_submission import AssessmentSubmission

    registry = FormRegistry()
    submission_fields = {f.name for f in dataclasses.fields(AssessmentSubmission)}
    submission_fields.add("biological_sex")  # stored as `sex`
    registered_fields = {
        field
        for form_type in registry.get_registered_form_types()
        for field in registry.get_form_fields(form_type)
    }
    assert registered_fields - submission_fields == set()
