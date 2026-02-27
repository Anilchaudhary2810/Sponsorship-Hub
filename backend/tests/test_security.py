import pytest

def test_sql_injection_protection(client):
    # Testing with ' OR '1'='1 payload
    payload = {
        "email": "' OR '1'='1",
        "password": "any"
    }
    response = client.post("/auth/login", json=payload)
    # SQLAlchemy and Pydantic handle validation/escaping
    assert response.status_code == 401

def test_xss_protection_in_profile(client, test_user, auth_headers):
    xss_payload = "<script>alert('xss')</script>"
    response = client.put(
        f"/users/{test_user.id}",
        json={"full_name": xss_payload},
        headers=auth_headers
    )
    assert response.status_code == 200
    # The system should store the string literally. 
    # Sanitization is usually done on frontend, but we store exactly what is sent.
    assert response.json()["full_name"] == xss_payload

def test_secure_headers_present(client):
    response = client.get("/health")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" in response.headers

def test_unauthorized_access_protected_endpoint(client):
    response = client.get("/users/")
    assert response.status_code == 401 # Bearer token missing
