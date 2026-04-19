import json

import pytest
from fastapi import WebSocketDisconnect


def _login_for_cookie(client, email: str, password: str = "Password123") -> None:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def test_chat_history_empty(client, base_deal, auth_headers):
    deal, _ = base_deal
    response = client.get(f"/chat/history/{deal.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_chat_websocket_auth_required(client, base_deal):
    deal, _ = base_deal
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/chat/ws/{deal.id}"):
            pass


def test_chat_websocket_query_token_rejected(client, base_deal, auth_headers):
    deal, _ = base_deal
    token = auth_headers["Authorization"].split(" ")[1]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/chat/ws/{deal.id}?token={token}"):
            pass


def test_chat_websocket_unauthorized_user(client, base_deal, db):
    from backend.crud import pwd_context
    from backend.models import User

    deal, _ = base_deal
    outsider = User(
        full_name="Outsider",
        email="outsider_chat@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    db.add(outsider)
    db.commit()

    _login_for_cookie(client, str(getattr(outsider, "email", "")))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/chat/ws/{deal.id}"):
            pass


def test_chat_message_flow_cookie_auth(client, base_deal, auth_headers, test_user):
    deal, _ = base_deal
    _login_for_cookie(client, str(getattr(test_user, "email", "")))

    with client.websocket_connect(f"/chat/ws/{deal.id}") as websocket:
        websocket.send_text(json.dumps({"text": "Hello world"}))
        data = websocket.receive_json()
        assert data["text"] == "Hello world"
        assert data["sender_id"] == int(getattr(test_user, "id", 0))

    response = client.get(f"/chat/history/{deal.id}", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["content"] == "Hello world"


def test_chat_message_flow_subprotocol_auth(client, base_deal, auth_headers, test_user):
    deal, _ = base_deal
    token = auth_headers["Authorization"].split(" ")[1]

    with client.websocket_connect(
        f"/chat/ws/{deal.id}",
        subprotocols=["access_token", token],
    ) as websocket:
        websocket.send_text(json.dumps({"text": "Hello via subprotocol"}))
        data = websocket.receive_json()
        assert data["text"] == "Hello via subprotocol"
        assert data["sender_id"] == int(getattr(test_user, "id", 0))


def test_notifications_websocket_auth_cookie(client, test_user):
    _login_for_cookie(client, str(getattr(test_user, "email", "")))
    with client.websocket_connect(f"/ws/notifications/{int(getattr(test_user, 'id', 0))}") as websocket:
        assert websocket is not None


def test_notifications_websocket_query_token_rejected(client, test_user, auth_headers):
    token = auth_headers["Authorization"].split(" ")[1]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/notifications/{test_user.id}?token={token}"):
            pass


def test_notifications_websocket_wrong_user(client, test_user, db):
    from backend.crud import pwd_context
    from backend.models import User

    other = User(
        full_name="Other",
        email="other_notify@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    db.add(other)
    db.commit()

    _login_for_cookie(client, str(getattr(test_user, "email", "")))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/notifications/{int(getattr(other, 'id', 0))}"):
            pass


def test_notifications_websocket_connect_and_idle(client, test_user):
    _login_for_cookie(client, str(getattr(test_user, "email", "")))
    with client.websocket_connect(f"/ws/notifications/{int(getattr(test_user, 'id', 0))}") as websocket:
        assert websocket is not None
