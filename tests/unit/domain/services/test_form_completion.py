from app.domain.services.form_completion import is_form_completed

SLEEP_FIELDS = ["snoring", "tired", "observed_apnea", "neck_circumference"]


def test_form_is_completed_when_every_field_has_a_value():
    values = {"snoring": False, "tired": True, "observed_apnea": False}
    values["neck_circumference"] = 38.0

    assert is_form_completed(SLEEP_FIELDS, values) is True


def test_false_counts_as_an_answer():
    values = {field: False for field in SLEEP_FIELDS}

    assert is_form_completed(SLEEP_FIELDS, values) is True


def test_field_shared_with_another_form_does_not_complete_the_form():
    values = {"neck_circumference": 38.0}

    assert is_form_completed(SLEEP_FIELDS, values) is False


def test_missing_or_empty_values_leave_the_form_incomplete():
    values = {"snoring": True, "tired": True, "observed_apnea": None}

    assert is_form_completed(SLEEP_FIELDS, values) is False
    assert is_form_completed(["nordic_nmq_data"], {"nordic_nmq_data": {}}) is False


def test_completed_submission_completes_the_form_without_values():
    assert is_form_completed(SLEEP_FIELDS, {}, has_completed_submission=True) is True


def test_form_without_fields_is_only_completed_by_a_submission():
    assert is_form_completed([], {}) is False
    assert is_form_completed([], {}, has_completed_submission=True) is True
