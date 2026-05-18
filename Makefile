dev:
	uv run fastapi dev app/main.py

test:
	COVERAGE_CORE=sysmon uv run pytest

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(m)" || (echo 'Uso: make revision m="mensaje"' && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

downgrade:
	uv run alembic downgrade -1
