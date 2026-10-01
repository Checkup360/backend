# ADR 0002: Scores are stored as a health index (higher is healthier)

- Status: Accepted
- Date: 2026-10-01

## Context

The engine calculators normalized every clinical score to a 0-100 risk scale
(0 = lowest risk, 100 = highest risk). The backend stored that value as-is in
`risk_scores.normalized_value` and aggregated it into
`member_overall_scores.overall_score`, with thresholds assuming higher means
worse. Frontends interpreted the same fields in both directions depending on
the screen, and neutral field names (`normalized_value`, `overall_score`)
hid the direction. `risk_index` in analytics was an exact copy of
`average_score`.

## Decision

- Every score persisted or exposed outside the engine is a **health index**:
  0-100, where **higher means healthier**.
- Calculators keep expressing clinical severity as `risk_value` (internal to
  the engine). The only inversion in the system is
  `ScoreResult.health_index = 100 - risk_value` in
  `engine/app/domain/value_objects/score_result.py`. The engine API exposes
  `health_index` and never `risk_value`.
- Field and column names state the direction: `risk_scores.health_index` and
  `member_overall_scores.overall_health_index`.
- Overall risk labels are derived from the health index in a single domain
  service, `backend/app/domain/services/health_index_classification.py`
  (`>= 80` Low risk, `>= 50` Moderate risk, `< 50` Needs attention). These
  bands are equivalent to the previous risk bands (`<= 20`, `<= 50`).
- Content prioritization converts the health index to severity explicitly
  (`(100 - health_index) / 100`) in `member_risk_priorities.py`, so the CMS
  keeps receiving "higher weight = more urgent".
- `risk_index` was removed from the analytics API.

## Consequences

- Migration `a1b2c3d4e5f6` renames both columns and converts existing values
  with `100 - x`. The conversion is its own inverse, so the downgrade is exact.
- Migrations must not import application code. The backfill in
  `f1a8b9c0d2e3` contains a frozen copy of the risk-era calculation for this
  reason.
- Any new calculator must return `risk_value`; the direction invariant test
  (`engine/tests/unit/domain/test_score_direction_invariant.py`) asserts that
  its health index is high for the best clinical case and low for the worst.
- Frontend thresholds are not unified yet and are tracked separately.
