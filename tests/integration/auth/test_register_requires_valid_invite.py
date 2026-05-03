def test_register_requires_valid_invite(client):
    """Intento de registro con token inválido debe fallar con 400 e `invalid_invite`."""
    body = {"email": "newuser@example.com", "password": "StrongP@ssw0rd"}

    # Usamos un token que no existe en la DB
    response = client.post("/invites/this-token-does-not-exist/register", json=body)

    assert response.status_code == 400
    assert response.json() == {"detail": {"code": "invalid_invite"}}
