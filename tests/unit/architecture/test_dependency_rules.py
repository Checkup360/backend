import ast
from pathlib import Path

APP_ROOT = Path(__file__).parents[3] / "app"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def assert_layer_avoids(layer: str, forbidden_prefixes: tuple[str, ...]) -> None:
    violations: list[str] = []
    for path in (APP_ROOT / layer).rglob("*.py"):
        for module in imported_modules(path):
            if module.startswith(forbidden_prefixes):
                violations.append(f"{path.relative_to(APP_ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_domain_has_no_framework_or_outer_layer_dependencies():
    assert_layer_avoids(
        "domain",
        (
            "fastapi",
            "pydantic",
            "sqlalchemy",
            "app.application",
            "app.infrastructure",
            "app.presentation",
        ),
    )


def test_application_has_no_framework_or_adapter_dependencies():
    assert_layer_avoids(
        "application",
        (
            "fastapi",
            "pydantic",
            "sqlalchemy",
            "app.infrastructure",
            "app.presentation",
        ),
    )


def test_api_routers_do_not_access_persistence_directly():
    assert_layer_avoids(
        "presentation/api/routers",
        ("sqlalchemy", "app.infrastructure.persistence"),
    )
