from typing import Any
import uuid

from app.application.dto.member_data_export import (
    ExportedConsentDTO,
    ExportedEvaluationDTO,
    ExportedProfileDTO,
    ExportedSubmissionDTO,
    MemberDataExportDTO,
)
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user_consent import ConsentType
from app.domain.exceptions import UserNotFoundError
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.member_health_data import MemberHealthDataRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.organization import OrganizationRepository
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.repositories.user import UserRepository
from app.domain.repositories.user_consent import UserConsentRepository
from app.domain.services.time_provider import TimeProvider

CONSENT_TYPE_NAMES: dict[str, str] = {
    "TERMS_AND_CONDITIONS": "Terms and Conditions",
    "PRIVACY_POLICY": "Privacy Policy",
    "HEALTH_DATA_PROCESSING_CONSENT": "Health Data Processing Consent",
    "FORM_CONSENT": "Form Data Consent",
}

FORM_TYPE_NAMES: dict[str, str] = {
    "biometrics": "Physical Biometrics",
    "sleep": "Sleep Quality",
    "habits": "Lifestyle & Habits",
    "mood": "Mood & Well-being",
    "metabolic": "Metabolic Health",
    "eoss": "Obesity-related Health Impact",
    "nordic_nmq": "Musculoskeletal Risk",
    "audit_c": "Alcohol Risk Assessment",
    "pss10": "Perceived Stress & Burnout",
    "health_history": "Health History",
}

SCORE_INDICATOR_NAMES: dict[str, str] = {
    "score2": "Cardiovascular Risk",
    "cardiovascular": "Cardiovascular Risk",
    "findrisc": "Type 2 Diabetes Risk",
    "diabetes": "Type 2 Diabetes Risk",
    "stop_bang": "Sleep Quality",
    "stopbang": "Sleep Quality",
    "sleep": "Sleep Quality",
    "phq9": "Mood & Well-being",
    "phq-9": "Mood & Well-being",
    "phq": "Mood & Well-being",
    "mood": "Mood & Well-being",
    "metabolic": "Metabolic Health",
    "metabolic_syndrome": "Metabolic Health",
    "audit_c": "Alcohol Risk Assessment",
    "audit": "Alcohol Risk Assessment",
    "alcohol": "Alcohol Risk Assessment",
    "pss10": "Perceived Stress & Burnout",
    "pss": "Perceived Stress & Burnout",
    "stress": "Perceived Stress & Burnout",
    "eoss_clinical": "Obesity-related Health Impact",
    "eoss": "Obesity-related Health Impact",
    "obesity": "Obesity-related Health Impact",
    "nordic_nmq": "Musculoskeletal Risk",
    "nordic": "Musculoskeletal Risk",
    "nmq": "Musculoskeletal Risk",
    "musculoskeletal": "Musculoskeletal Risk",
}


class ExportMemberDataUseCase:
    """Use case to gather and export all personal and health data for a member in compliance with Habeas Data."""

    def __init__(
        self,
        user_repository: UserRepository,
        member_details_repository: MemberDetailsRepository,
        membership_repository: MembershipRepository,
        organization_repository: OrganizationRepository,
        user_consent_repository: UserConsentRepository,
        member_health_data_repository: MemberHealthDataRepository,
        assessment_submission_repository: AssessmentSubmissionRepository,
        risk_score_repository: RiskScoreRepository,
        audit_log_repository: AuditLogRepository,
        time_provider: TimeProvider,
    ) -> None:
        self._user_repository = user_repository
        self._member_details_repository = member_details_repository
        self._membership_repository = membership_repository
        self._organization_repository = organization_repository
        self._user_consent_repository = user_consent_repository
        self._member_health_data_repository = member_health_data_repository
        self._assessment_submission_repository = assessment_submission_repository
        self._risk_score_repository = risk_score_repository
        self._audit_log_repository = audit_log_repository
        self._time_provider = time_provider

    async def execute(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> MemberDataExportDTO:
        user = await self._user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError()

        now = self._time_provider.utcnow()

        # 1. Profile and demographic details (internal IDs sanitized)
        details = await self._member_details_repository.get_by_user(user_id)
        membership = await self._membership_repository.get_by_user(user_id)

        org_name: str | None = None
        org_id: uuid.UUID | None = None
        roles: list[str] = []
        if membership:
            org_id = membership.organization_id
            roles = [r.value for r in membership.roles]
            org = await self._organization_repository.get(membership.organization_id)
            if org:
                org_name = org.name

        profile_dto = ExportedProfileDTO(
            email=user.email,
            first_name=details.first_name if details else None,
            last_name=details.last_name if details else None,
            phone_number=details.phone_number if details else None,
            date_of_birth=details.date_of_birth if details else None,
            avatar_url=details.avatar_url if details else None,
            organization=org_name,
            roles=roles,
        )

        # 2. Historical and active consents (internal IDs stripped, friendly naming)
        raw_consents = await self._user_consent_repository.list_by_user_id(user_id)
        consent_dtos: list[ExportedConsentDTO] = []
        for c in raw_consents:
            raw_type = (
                c.consent_type.value
                if isinstance(c.consent_type, ConsentType)
                else str(c.consent_type)
            )

            if raw_type == "FORM_CONSENT" and c.form_type:
                form_label = FORM_TYPE_NAMES.get(c.form_type, c.form_type.title())
                friendly_type = f"Form Consent: {form_label}"
            else:
                friendly_type = CONSENT_TYPE_NAMES.get(
                    raw_type, raw_type.replace("_", " ").title()
                )

            consent_dtos.append(
                ExportedConsentDTO(
                    type=friendly_type,
                    version=c.document_version,
                    accepted_at=c.accepted_at,
                    revoked_at=c.revoked_at,
                    status="Revoked" if c.revoked_at else "Active",
                )
            )

        # 3. Health measurements (null fields stripped)
        health_data = await self._member_health_data_repository.get_by_user(user_id)
        health_measurements: dict[str, Any] = {}
        if health_data:
            raw_measurements = {
                "biological_sex": health_data.biological_sex,
                "height": health_data.height,
                "weight": health_data.weight,
                "neck_circumference": health_data.neck_circumference,
                "waist_circumference": health_data.waist_circumference,
                "systolic_blood_pressure": health_data.systolic_blood_pressure,
                "diastolic_blood_pressure": health_data.diastolic_blood_pressure,
                "total_cholesterol": health_data.total_cholesterol,
                "hdl_cholesterol": health_data.hdl_cholesterol,
                "triglycerides": health_data.triglycerides,
                "fasting_glucose": health_data.fasting_glucose,
                "glucose_lowering_medication": health_data.glucose_lowering_medication,
                "statins": health_data.statins,
                "lab_study_date": health_data.lab_study_date.isoformat()
                if health_data.lab_study_date
                else None,
                "hypertension_medication": health_data.hypertension_medication,
                "daily_physical_activity": health_data.daily_physical_activity,
                "fruits_vegetables": health_data.fruits_vegetables,
                "previous_high_glucose": health_data.previous_high_glucose,
                "family_diabetes": health_data.family_diabetes,
                "smoker": health_data.smoker,
                "snoring": health_data.snoring,
                "tired": health_data.tired,
                "observed_apnea": health_data.observed_apnea,
                "eoss_physical_health_stage": health_data.eoss_physical_health_stage,
                "eoss_mental_health_stage": health_data.eoss_mental_health_stage,
                "eoss_functional_stage": health_data.eoss_functional_stage,
            }
            health_measurements = {
                k: v for k, v in raw_measurements.items() if v is not None
            }

        # 4. Assessment submissions (internal IDs stripped, friendly names)
        submissions_tuple = await self._assessment_submission_repository.list_by_user(
            user_id, offset=0, limit=200
        )
        submissions = (
            submissions_tuple[0]
            if isinstance(submissions_tuple, tuple)
            else submissions_tuple
        )
        submissions_list: list[ExportedSubmissionDTO] = []
        for sub in submissions:
            answers = {
                k: v
                for k, v in sub.__dict__.items()
                if not k.startswith("_")
                and k
                not in {
                    "id",
                    "user_id",
                    "organization_id",
                    "form_type",
                    "form_version",
                    "status",
                    "submitted_at",
                    "consent_id",
                }
                and v is not None
            }
            submissions_list.append(
                ExportedSubmissionDTO(
                    form_type=sub.form_type,
                    form_name=FORM_TYPE_NAMES.get(
                        sub.form_type, sub.form_type.replace("_", " ").title()
                    ),
                    form_version=sub.form_version,
                    status=sub.status,
                    submitted_at=sub.submitted_at.isoformat()
                    if sub.submitted_at
                    else None,
                    answers=answers,
                )
            )

        # 5. Risk score evaluations mapped to friendly health indicators (all historical records preserved)
        risk_scores = await self._risk_score_repository.get_by_user_id(user_id)
        evaluations_list: list[ExportedEvaluationDTO] = []
        for score in risk_scores:
            indicator_name = SCORE_INDICATOR_NAMES.get(
                score.score_name.lower(),
                score.score_name.replace("_", " ").title(),
            )
            evaluations_list.append(
                ExportedEvaluationDTO(
                    indicator=indicator_name,
                    risk_level=score.risk_level,
                    evaluated_at=score.evaluated_at.isoformat()
                    if score.evaluated_at
                    else None,
                )
            )

        # 6. Record Audit Log entry for the data export
        audit_entry = AuditLog.create(
            action="DATA_EXPORTED",
            resource_type="MEMBER_PERSONAL_DATA",
            user_id=user_id,
            organization_id=org_id,
            resource_id=str(user_id),
            details={
                "consents_count": len(consent_dtos),
                "submissions_count": len(submissions_list),
                "evaluations_count": len(evaluations_list),
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )
        await self._audit_log_repository.log(audit_entry)

        return MemberDataExportDTO(
            profile=profile_dto,
            consents=consent_dtos,
            health_measurements=health_measurements,
            assessment_history=submissions_list,
            health_evaluations=evaluations_list,
            exported_at=now,
        )
