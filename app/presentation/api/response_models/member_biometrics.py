from pydantic import BaseModel


class MemberBiometricsResponse(BaseModel):
    biological_sex: str | None = None
    height: float | None = None
    weight: float | None = None
    waist_circumference: float | None = None
    neck_circumference: float | None = None
