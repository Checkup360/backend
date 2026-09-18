"""Unit tests for Health Domain entities, dependency matrix, and two-phase score engine."""

from app.domain.entities.health_domain import (
    HealthDomain,
    InputFormModule,
)
from app.domain.services.domain_dependency_matrix import DomainDependencyMatrix
from app.domain.services.two_phase_score_engine import TwoPhaseScoreEngine


def test_health_domain_enum_values():
    assert HealthDomain.CARDIOMETABOLIC.value == "cardiometabolic"
    assert HealthDomain.FATIGUE_SLEEP.value == "fatigue_sleep"
    assert HealthDomain.MENTAL_HEALTH.value == "mental_health"


def test_input_form_module_enum_values():
    assert InputFormModule.BASE_BIOMETRICS.value == "base_biometrics"
    assert InputFormModule.LABORATORY_CLINIC.value == "laboratory_clinic"
    assert InputFormModule.LIFESTYLE_HABITS.value == "lifestyle_habits"
    assert InputFormModule.OPERATIONAL_FATIGUE.value == "operational_fatigue"
    assert InputFormModule.PSYCHOLOGICAL_HEALTH.value == "psychological_health"


def test_base_biometrics_is_always_immutable_and_active():
    matrix = DomainDependencyMatrix()
    # Empty active domains list
    active_modules = matrix.get_active_form_modules(domain_weights={})
    assert InputFormModule.BASE_BIOMETRICS in active_modules
    assert len(active_modules) == 1


def test_dependency_matrix_cardiometabolic_only():
    matrix = DomainDependencyMatrix()
    weights = {
        HealthDomain.CARDIOMETABOLIC.value: 100.0,
        HealthDomain.FATIGUE_SLEEP.value: 0.0,
        HealthDomain.MENTAL_HEALTH.value: 0.0,
    }
    active_modules = matrix.get_active_form_modules(domain_weights=weights)
    assert active_modules == {
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.LABORATORY_CLINIC,
        InputFormModule.LIFESTYLE_HABITS,
    }


def test_dependency_matrix_fatigue_sleep_only():
    matrix = DomainDependencyMatrix()
    weights = {
        HealthDomain.CARDIOMETABOLIC.value: 0.0,
        HealthDomain.FATIGUE_SLEEP.value: 100.0,
        HealthDomain.MENTAL_HEALTH.value: 0.0,
    }
    active_modules = matrix.get_active_form_modules(domain_weights=weights)
    assert active_modules == {
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.OPERATIONAL_FATIGUE,
    }


def test_dependency_matrix_mental_health_only():
    matrix = DomainDependencyMatrix()
    weights = {
        HealthDomain.CARDIOMETABOLIC.value: 0.0,
        HealthDomain.FATIGUE_SLEEP.value: 0.0,
        HealthDomain.MENTAL_HEALTH.value: 100.0,
    }
    active_modules = matrix.get_active_form_modules(domain_weights=weights)
    assert active_modules == {
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.PSYCHOLOGICAL_HEALTH,
    }


def test_dependency_matrix_intersection_all_active():
    matrix = DomainDependencyMatrix()
    weights = {
        HealthDomain.CARDIOMETABOLIC.value: 40.0,
        HealthDomain.FATIGUE_SLEEP.value: 30.0,
        HealthDomain.MENTAL_HEALTH.value: 30.0,
    }
    active_modules = matrix.get_active_form_modules(domain_weights=weights)
    assert active_modules == {
        InputFormModule.BASE_BIOMETRICS,
        InputFormModule.LABORATORY_CLINIC,
        InputFormModule.LIFESTYLE_HABITS,
        InputFormModule.OPERATIONAL_FATIGUE,
        InputFormModule.PSYCHOLOGICAL_HEALTH,
    }


def test_two_phase_score_engine_phase_1_and_phase_2():
    engine = TwoPhaseScoreEngine()

    # Sub-scores per test calculator
    calculator_scores = {
        "diabetes": 20.0,
        "metabolic_syndrome": 30.0,
        "cardiovascular": 10.0,
        "sleep_apnea": 40.0,
        "depression": 50.0,
        "eoss": 10.0,
    }

    domain_weights = {
        HealthDomain.CARDIOMETABOLIC.value: 50.0,
        HealthDomain.FATIGUE_SLEEP.value: 25.0,
        HealthDomain.MENTAL_HEALTH.value: 25.0,
    }

    # Phase 1: Calculate Domain Scores
    domain_scores = engine.calculate_domain_scores(calculator_scores)

    # Cardiometabolic = avg(20, 30, 10) = 20.0
    assert domain_scores[HealthDomain.CARDIOMETABOLIC].normalized_score == 20.0
    # Fatigue & Sleep = 40.0
    assert domain_scores[HealthDomain.FATIGUE_SLEEP].normalized_score == 40.0
    # Mental Health = avg(50, 10) = 30.0
    assert domain_scores[HealthDomain.MENTAL_HEALTH].normalized_score == 30.0

    # Phase 2: Weighted Global Index
    global_index = engine.calculate_global_weighted_index(domain_scores, domain_weights)

    # Expected overall = (20*50 + 40*25 + 30*25) / 100 = (1000 + 1000 + 750) / 100 = 27.5
    assert global_index.overall_score == 27.5
    assert global_index.risk_level == "Moderate risk"
