# Backend (FastAPI + uv)

Backend API construido con FastAPI y gestionado con `uv`.

## Requisitos

- Python 3.12+
- uv (Astral)

Instalar uv si no lo tienes:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Crear venv e instalar las dependencias:

```bash
uv venv
uv sync
```

## Pre-commit

Instalar los hooks:

```bash
uv run pre-commit install
```

## Ejecutar en modo desarrollo

```bash
uv run uvicorn app.presentation.main:app --reload
```

## Arquitectura

El backend utiliza arquitectura hexagonal con dependencias dirigidas hacia el
dominio:

```text
Presentation -> Application -> Domain
Infrastructure -> Application -> Domain
```

- `app/domain`: entidades, value objects, reglas e interfaces de repositorios.
- `app/application`: casos de uso, DTOs e interfaces para servicios externos.
- `app/infrastructure`: SQLAlchemy, PostgreSQL, autenticación, SMTP y configuración.
- `app/presentation`: FastAPI, rutas, modelos HTTP e inyección de dependencias.

El dominio no puede importar FastAPI, Pydantic, SQLAlchemy ni infraestructura.
Los controladores no acceden directamente a la base de datos.

La decisión completa está documentada en
[`docs/adr/0001-hexagonal-backend-structure.md`](docs/adr/0001-hexagonal-backend-structure.md).
