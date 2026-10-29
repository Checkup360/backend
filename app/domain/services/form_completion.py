"""When a health form counts as completed for a member.

A form is completed when the member has a completed submission of it, or when
every field the form asks for has a value. Fields shared between forms (such
as the neck circumference) must not mark a form as completed on their own.
"""

from collections.abc import Collection, Mapping


def has_value(value: object) -> bool:
    return value is not None and value != {}


def is_form_completed(
    fields: Collection[str],
    health_values: Mapping[str, object],
    has_completed_submission: bool = False,
) -> bool:
    if has_completed_submission:
        return True
    if not fields:
        return False
    return all(has_value(health_values.get(field)) for field in fields)
