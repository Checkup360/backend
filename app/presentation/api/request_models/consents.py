from pydantic import BaseModel, Field


class AcceptConsentRequest(BaseModel):
    consent_type: str = Field(
        ...,
        description="Type of consent: TERMS_AND_CONDITIONS, PRIVACY_POLICY, HEALTH_DATA_PROCESSING_CONSENT, or FORM_CONSENT",
        examples=["FORM_CONSENT"],
    )
    form_type: str | None = Field(
        default=None,
        description="Form type required when consent_type is FORM_CONSENT (e.g. biometrics, mood, sleep)",
        examples=["biometrics"],
    )
    document_version: str = Field(
        default="1",
        description="Version string of the legal document or form specification",
        examples=["1"],
    )
    document_hash: str | None = Field(
        default=None,
        description="Cryptographic SHA-256 hash of the consented document text",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )
