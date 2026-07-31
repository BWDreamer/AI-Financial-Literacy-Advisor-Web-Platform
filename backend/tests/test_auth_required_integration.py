def test_private_user_routes_require_authentication(client):
    private_requests = [
        ("GET", "/api/profile", None),
        (
            "PUT",
            "/api/profile",
            {
                "region": "NSW",
                "monthly_income": 5000,
                "fixed_expenses": 2500,
                "current_savings": 10000,
                "initial_savings_target": 20000,
            },
        ),
        ("GET", "/api/financials", None),
        ("GET", "/api/financials/summary", None),
        (
            "POST",
            "/api/financials/assets",
            {"asset_type": "cash", "name": "Savings", "amount": "100.00"},
        ),
        ("GET", "/api/goals", None),
        ("GET", "/api/goals/summary", None),
        ("GET", "/api/memory", None),
        (
            "POST",
            "/api/memory",
            {"category": "preference", "fact": "I prefer simple advice."},
        ),
        ("GET", "/api/chat/conversations", None),
        (
            "POST",
            "/api/ai/chat",
            {"message": "Explain compound interest."},
        ),
        ("POST", "/api/auth/heartbeat", None),
    ]

    for method, path, json_payload in private_requests:
        response = client.request(method, path, json=json_payload)
        assert response.status_code == 401, f"{method} {path}"


def test_admin_routes_require_authentication(client):
    admin_requests = [
        ("GET", "/api/admin/users", None),
        (
            "POST",
            "/api/admin/users",
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "password": "Password123",
            },
        ),
        ("GET", "/api/admin/advisory-settings", None),
        (
            "PATCH",
            "/api/admin/advisory-settings",
            {"topics": [{"name": "Budgeting", "enabled": False}]},
        ),
        (
            "POST",
            "/api/admin/articles",
            {
                "id": "private-admin-article",
                "title": "Private",
                "summary": "Admin only",
                "authorName": "Admin",
                "sourceName": "Knowledge Base",
                "category": "Budgeting",
                "contentBlocks": [],
            },
        ),
    ]

    for method, path, json_payload in admin_requests:
        response = client.request(method, path, json=json_payload)
        assert response.status_code == 401, f"{method} {path}"
