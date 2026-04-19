from backend.models import AuditEvent


def test_submit_kyc_and_read_trust_profile(client, auth_headers):
    submit_resp = client.post(
        "/trust/kyc/submit",
        headers=auth_headers,
        json={
            "document_type": "pan",
            "document_number_masked": "ABCDE1234X",
            "document_url": "https://example.com/doc.png",
        },
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "pending"

    trust_resp = client.get("/trust/me", headers=auth_headers)
    assert trust_resp.status_code == 200
    payload = trust_resp.json()
    assert payload["kyc_status"] == "pending"
    assert payload["latest_submission"] is not None


def test_pending_kyc_requires_admin(client, auth_headers, admin_auth_headers):
    client.post(
        "/trust/kyc/submit",
        headers=auth_headers,
        json={
            "document_type": "aadhaar",
            "document_number_masked": "XXXX-XXXX-1234",
            "document_url": None,
        },
    )

    forbidden = client.get("/trust/kyc/pending", headers=auth_headers)
    assert forbidden.status_code == 403

    admin_ok = client.get("/trust/kyc/pending", headers=admin_auth_headers)
    assert admin_ok.status_code == 200
    assert isinstance(admin_ok.json(), list)
    assert len(admin_ok.json()) >= 1


def test_admin_review_kyc_approves_badge(client, db, auth_headers, admin_auth_headers, test_user):
    submit_resp = client.post(
        "/trust/kyc/submit",
        headers=auth_headers,
        json={
            "document_type": "passport",
            "document_number_masked": "P1234567",
            "document_url": None,
        },
    )
    submission_id = submit_resp.json()["id"]

    review_resp = client.put(
        f"/trust/kyc/{submission_id}/review",
        headers=admin_auth_headers,
        json={"decision": "approved", "review_note": "Verified"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"

    db.refresh(test_user)
    assert bool(test_user.verification_badge) is True


def test_trust_profile_reports_token_reuse_flag(client, db, auth_headers, test_user):
    evt = AuditEvent(
        action="auth.refresh_reuse_detected",
        actor_user_id=test_user.id,
        target_type="user",
        target_id=test_user.id,
        event_meta={"source": "test"},
    )
    db.add(evt)
    db.commit()

    trust_resp = client.get("/trust/me", headers=auth_headers)
    assert trust_resp.status_code == 200
    payload = trust_resp.json()
    assert "token_reuse_signal" in payload["risk_flags"]
    assert payload["risk_level"] == "high"
