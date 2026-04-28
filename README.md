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

## Ejecutar en modo desarrollo

```bash
uv run uvicorn main:app --reload
```
