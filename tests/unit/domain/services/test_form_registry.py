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
