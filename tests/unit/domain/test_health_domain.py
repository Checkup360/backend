"""Unit tests for Health Domain entities, and dependency matrix."""

from app.domain.entities.health_domain import (
    HealthDomain,
    InputFormModule,
)
from app.domain.services.domain_dependency_matrix import DomainDependencyMatrix


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
