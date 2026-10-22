"""Free-text search applied to the employees of an organization.

A term matches an employee when it is contained in their email, department,
first name, last name or full name. Matching ignores case and accents, so the
persistence layer must compare against terms normalized the same way.
"""

import unicodedata


def normalize_search_term(term: str) -> str:
    decomposed = unicodedata.normalize("NFKD", term.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
