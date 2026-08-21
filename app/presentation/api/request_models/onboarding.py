from app.presentation.api.request_models.member_biometrics import (
    MemberBiometricsCreate,
)
from app.presentation.api.request_models.member_details import MemberDetailsCreate


class OnboardingRequest(MemberDetailsCreate, MemberBiometricsCreate):
    pass
