"""RFC 9457 problem+json error responses wired by fastapi-problem-details.

Pins what the frontend's error extraction relies on: problem+json as
the error media type, the `detail` string on every raised error, and
validation errors normalized to a fixed detail with the specifics in
an `errors` member.
"""

from fastapi.testclient import TestClient


def test_error_responses_are_problem_json_with_detail(client: TestClient) -> None:
    response = client.get("/api/images/nonexistent")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "image not found"


def test_validation_errors_normalize_to_problem(client: TestClient) -> None:
    response = client.get("/api/images", params={"kind": "bogus"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["detail"] == "Request validation failed"
    assert isinstance(body["errors"], list)


def test_handler_rejections_keep_detail(client: TestClient) -> None:
    response = client.get("/api/images/nope/b30_prefill/0", params={"layout": "bogus"})
    assert response.status_code == 422
    assert response.json()["detail"] == "unknown layout: bogus"
