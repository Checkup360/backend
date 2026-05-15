"""Respuestas JSON construidas desde modelos Pydantic (sin dicts sueltos)."""

from pydantic import BaseModel
from starlette.responses import Response


def response_json(model: BaseModel, *, status_code: int = 200) -> Response:
    return Response(
        content=model.model_dump_json(),
        status_code=status_code,
        media_type="application/json",
    )
