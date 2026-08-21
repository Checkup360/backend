from pydantic import BaseModel


class MemberBiometricsCreate(BaseModel):
    biological_sex: str | None = None
    height: float | None = None
    weight: float | None = None
