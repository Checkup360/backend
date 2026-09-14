from app.domain.services.organization_form_policy import OrganizationFormPolicy


def test_get_active_form_types_default_weights():
    policy = OrganizationFormPolicy()
    active_forms = policy.get_active_form_types(score_weights=None)
    assert set(active_forms) == {
        "biometrics",
        "sleep",
        "habits",
        "metabolic",
        "eoss",
        "mood",
    }


def test_get_active_form_types_empty_dict():
    policy = OrganizationFormPolicy()
    active_forms = policy.get_active_form_types(score_weights={})
    assert set(active_forms) == {
        "biometrics",
        "sleep",
        "habits",
        "metabolic",
        "eoss",
        "mood",
    }


def test_get_active_form_types_disabled_depression():
    policy = OrganizationFormPolicy()
    weights = {"diabetes": 50.0, "sleep_apnea": 50.0, "depression": 0.0}
    active_forms = policy.get_active_form_types(score_weights=weights)
    assert "mood" not in active_forms
    assert "sleep" in active_forms
    assert "habits" in active_forms
    assert "biometrics" in active_forms


def test_get_active_form_types_disabled_sleep_apnea():
    policy = OrganizationFormPolicy()
    weights = {"diabetes": 50.0, "sleep_apnea": 0.0, "depression": 50.0}
    active_forms = policy.get_active_form_types(score_weights=weights)
    assert "sleep" not in active_forms
    assert "mood" in active_forms


def test_get_active_form_types_disabled_all_except_diabetes():
    policy = OrganizationFormPolicy()
    weights = {
        "diabetes": 100.0,
        "sleep_apnea": 0.0,
        "depression": 0.0,
        "metabolic_syndrome": 0.0,
        "eoss": 0.0,
        "cardiovascular": 0.0,
    }
    active_forms = policy.get_active_form_types(score_weights=weights)
    # Diabetes requires biometrics and habits
    assert set(active_forms) == {"biometrics", "habits"}


def test_get_active_form_definitions():
    policy = OrganizationFormPolicy()
    weights = {"depression": 0.0, "sleep_apnea": 0.0, "eoss": 0.0}
    active_defs = policy.get_active_form_definitions(score_weights=weights)
    form_types = [form.form_type for form in active_defs]
    assert "mood" not in form_types
    assert "sleep" not in form_types
    assert "eoss" not in form_types
    assert "biometrics" in form_types
