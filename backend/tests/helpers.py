def register_verified_user(client, payload: dict):
    email = str(payload["email"]).lower()
    sent = client.post(
        "/api/auth/register/verification-code",
        json={"email": email},
    )
    assert sent.status_code == 200
    code = client.sent_verification_codes[email]
    return client.post(
        "/api/auth/register",
        json={**payload, "verification_code": code},
    )
