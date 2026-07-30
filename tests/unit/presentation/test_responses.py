from pydantic import BaseModel
from app.presentation.api.responses import response_json


class DummyModel(BaseModel):
    name: str
    count: int


def test_response_json_helper():
    model = DummyModel(name="test", count=42)
    res = response_json(model, status_code=201)

    assert res.status_code == 201
    assert res.media_type == "application/json"
    assert res.body == b'{"name":"test","count":42}'
