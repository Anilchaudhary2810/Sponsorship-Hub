"""
Event route tests – covers CRUD for /events.
Note: current events router has no auth guard; tests reflect actual behaviour.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def organizer_user(db):
    from backend.models import User
    from backend.crud import pwd_context
    user = User(
        full_name="Org User",
        email="org_events@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_event(db, organizer_user):
    from backend.models import Event
    event = Event(
        title="Test Event",
        description="An event for testing",
        organizer_id=organizer_user.id,
        currency="INR"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_create_event_success(client, organizer_user):
    response = client.post(
        "/events/",
        json={
            "title": "New Conference",
            "description": "Tech summit",
            "organizer_id": organizer_user.id,
            "currency": "INR"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Conference"
    assert data["organizer_id"] == organizer_user.id


def test_create_event_missing_required_fields(client):
    """Missing title and organizer_id should return 422."""
    response = client.post("/events/", json={"description": "No title"})
    assert response.status_code == 422


def test_create_event_invalid_date_format(client, organizer_user):
    """Malformed date string should be rejected."""
    response = client.post(
        "/events/",
        json={
            "title": "Bad Date Event",
            "organizer_id": organizer_user.id,
            "date": "not-a-date"
        }
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Read / List
# ---------------------------------------------------------------------------

def test_list_events(client, sample_event):
    response = client.get("/events/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_event_by_id(client, sample_event):
    response = client.get(f"/events/{sample_event.id}")
    assert response.status_code == 200
    assert response.json()["id"] == sample_event.id
    assert response.json()["title"] == "Test Event"


def test_get_event_not_found(client):
    response = client.get("/events/999999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_event_success(client, sample_event):
    response = client.put(
        f"/events/{sample_event.id}",
        json={"title": "Updated Title", "description": "New desc"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_event_partial(client, sample_event):
    """Only fields provided in the body are updated."""
    response = client.put(
        f"/events/{sample_event.id}",
        json={"city": "Mumbai"}
    )
    assert response.status_code == 200
    assert response.json()["city"] == "Mumbai"
    assert response.json()["title"] == "Test Event"  # unchanged


def test_update_event_not_found(client):
    response = client.put("/events/999999", json={"title": "Ghost"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_event_success(client, sample_event):
    response = client.delete(f"/events/{sample_event.id}")
    assert response.status_code == 200

    # Confirm it's gone
    get_response = client.get(f"/events/{sample_event.id}")
    assert get_response.status_code == 404


def test_delete_event_not_found(client):
    response = client.delete("/events/999999")
    assert response.status_code == 404
