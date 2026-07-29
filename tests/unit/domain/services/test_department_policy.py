import pytest

from app.domain.services.department_policy import build_department_slug


def test_build_department_slug_normalizes_accents_and_spaces():
    assert (
        build_department_slug("  Administración de Personal  ")
        == "administracion-de-personal"
    )


def test_build_department_slug_replaces_special_characters_with_hyphens():
    assert build_department_slug("IT & DevOps (Core)") == "it-devops-core"


@pytest.mark.parametrize("invalid_name", ["", "   ", "!!!", "@#$%^&*"])
def test_build_department_slug_raises_value_error_for_empty_or_symbol_only_name(
    invalid_name,
):
    with pytest.raises(ValueError, match="invalid_department_name"):
        build_department_slug(invalid_name)
