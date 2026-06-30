def auth_headers(client, email: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_conversation_and_message_crud(client):
    headers = auth_headers(client, "chat@example.com")
    created = client.post(
        "/api/chat/conversations",
        headers=headers,
        json={},
    )
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]

    message = client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={"role": "user", "content": "What is compound interest?"},
    )
    assert message.status_code == 201

    conversations = client.get("/api/chat/conversations", headers=headers)
    assert conversations.status_code == 200
    assert conversations.json()[0]["title"] == "What is compound interest?"

    detail = client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    )
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["role"] == "user"

    assert client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    ).status_code == 204
    assert client.get(
        f"/api/chat/conversations/{conversation_id}", headers=headers
    ).status_code == 404


def test_conversation_ownership(client):
    first = auth_headers(client, "first-chat@example.com")
    second = auth_headers(client, "second-chat@example.com")
    conversation_id = client.post(
        "/api/chat/conversations", headers=first, json={"title": "Private"}
    ).json()["conversation_id"]

    assert client.get(
        f"/api/chat/conversations/{conversation_id}", headers=second
    ).status_code == 404
    assert client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=second,
        json={"role": "user", "content": "Not mine"},
    ).status_code == 404
    assert client.delete(
        f"/api/chat/conversations/{conversation_id}", headers=second
    ).status_code == 404


def test_chat_message_validation(client):
    headers = auth_headers(client, "validation-chat@example.com")
    conversation_id = client.post(
        "/api/chat/conversations", headers=headers, json={}
    ).json()["conversation_id"]
    assert client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={"role": "system", "content": "invalid"},
    ).status_code == 422
    assert client.post(
        f"/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={"role": "user", "content": "   "},
    ).status_code == 422
