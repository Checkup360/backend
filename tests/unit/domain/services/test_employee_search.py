import pytest

from app.domain.services.employee_search import normalize_search_term


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("Matías", "matias"),
        ("  BESMEDRISNIK ", "besmedrisnik"),
        ("Ñandú", "nandu"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_search_term_ignores_case_accents_and_padding(term, expected):
    assert normalize_search_term(term) == expected
