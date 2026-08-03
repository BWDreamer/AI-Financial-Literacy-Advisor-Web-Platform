def test_api_index_and_health(client):
    index = client.get("/api")
    assert index.status_code == 200
    assert index.json()["name"] == "AI Financial Literacy Advisor API"
    assert index.json()["docs_url"] == "/docs"
    assert "/api/admin/articles" in index.json()["groups"]["administration"]

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["version"] == index.json()["version"]


def test_openapi_exposes_resource_friendly_interfaces(client):
    schema = client.get("/openapi.json").json()
    expected_paths = {
        "/api",
        "/api/financials/assets",
        "/api/financials/assets/{asset_id}",
        "/api/financials/cash-buckets/{bucket_id}",
        "/api/financials/cash-flows",
        "/api/financials/cash-flows/{cash_flow_id}",
        "/api/financials/debts/{debt_id}",
        "/api/financials/recurring-cash-flows/{recurring_id}",
        "/api/memory/{memory_id}",
        "/api/admin/users/{user_id}",
        "/api/admin/articles",
        "/api/admin/articles/{article_id}",
    }
    assert expected_paths <= set(schema["paths"])

    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))
