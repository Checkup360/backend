"""backfill historical consents to audit_logs

Revision ID: f7c8d9e0f1a2
Revises: f6b7c8d9e0f1
Create Date: 2026-09-29 16:48:00.000000

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill accepted consents
    op.execute(
        """
        INSERT INTO audit_logs (id, user_id, organization_id, action, resource_type, resource_id, details, created_at)
        SELECT
            gen_random_uuid(),
            uc.user_id,
            m.organization_id,
            'CONSENT_ACCEPTED',
            'USER_CONSENT',
            uc.id::text,
            json_build_object(
                'consent_type', uc.consent_type,
                'form_type', uc.form_type,
                'document_version', uc.document_version,
                'document_hash', uc.document_hash,
                'ip_address', uc.ip_address,
                'user_agent', uc.user_agent,
                'source', 'historical_backfill'
            )::jsonb,
            uc.accepted_at
        FROM user_consents uc
        LEFT JOIN memberships m ON m.user_id = uc.user_id
        WHERE NOT EXISTS (
            SELECT 1 FROM audit_logs al
            WHERE al.resource_type = 'USER_CONSENT'
            AND al.resource_id = uc.id::text
            AND al.action = 'CONSENT_ACCEPTED'
        );
        """
    )

    # 2. Backfill revoked consents
    op.execute(
        """
        INSERT INTO audit_logs (id, user_id, organization_id, action, resource_type, resource_id, details, created_at)
        SELECT
            gen_random_uuid(),
            uc.user_id,
            m.organization_id,
            'CONSENT_REVOKED',
            'USER_CONSENT',
            uc.id::text,
            json_build_object(
                'consent_type', uc.consent_type,
                'form_type', uc.form_type,
                'revoked_at', uc.revoked_at,
                'source', 'historical_backfill'
            )::jsonb,
            uc.revoked_at
        FROM user_consents uc
        LEFT JOIN memberships m ON m.user_id = uc.user_id
        WHERE uc.revoked_at IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM audit_logs al
            WHERE al.resource_type = 'USER_CONSENT'
            AND al.resource_id = uc.id::text
            AND al.action = 'CONSENT_REVOKED'
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM audit_logs
        WHERE details->>'source' = 'historical_backfill';
        """
    )
