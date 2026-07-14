import re
import unicodedata


def build_department_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        raise ValueError("invalid_department_name")
    return slug
