from datetime import date
from typing import Sequence

from app.domain.entities import MemberDetails

# Temas estándar que coinciden con las opciones de diseaseTypes en Payload CMS
CMS_DISEASE_TOPICS: list[str] = [
    "cardiovascular",
    "diabetes",
    "respiratory",
    "oncology",
    "neurology",
]


def calculate_member_priority_topics(
    member_details: MemberDetails | None,
    available_topics: Sequence[str] = CMS_DISEASE_TOPICS,
) -> list[str]:
    """
    Determina el orden de prioridad médica de los temas de salud para un miembro.

    Esta regla de dominio pura evalúa los factores de salud/edad del perfil del miembro
    y devuelve la lista de topics ordenada por relevancia.
    """
    if member_details is None:
        return list(available_topics)

    # Cálculo de edad para determinar riesgos preventivos primarios
    today = date.today()
    age = (
        today.year
        - member_details.date_of_birth.year
        - (
            (today.month, today.day)
            < (member_details.date_of_birth.month, member_details.date_of_birth.day)
        )
    )

    if age >= 50:
        ordered = ["cardiovascular", "diabetes", "oncology", "respiratory", "neurology"]
    elif age >= 35:
        ordered = ["cardiovascular", "diabetes", "respiratory", "neurology", "oncology"]
    else:
        ordered = ["respiratory", "cardiovascular", "diabetes", "neurology", "oncology"]

    available_set = set(available_topics)
    result = [topic for topic in ordered if topic in available_set]
    for topic in available_topics:
        if topic not in result:
            result.append(topic)

    return result
