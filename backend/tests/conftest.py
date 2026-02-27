import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import os
import sys

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Base, get_db
from backend.main import app
from backend.models import User
from backend.crud import pwd_context
from backend.auth import create_access_token

# Use SQLite in-memory for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def disable_rate_limit():
    from backend.core.limiter import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    user_data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": pwd_context.hash("Password123"),
        "role": "sponsor",
        "is_verified": True
    }
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_admin(db):
    user_data = {
        "full_name": "Admin User",
        "email": "admin@example.com",
        "password": pwd_context.hash("Password123"),
        "role": "admin",
        "is_verified": True
    }
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(test_admin):
    token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def base_deal(db, test_user):
    from backend.models import User, Deal
    organizer = User(
        full_name="Organizer",
        email="org@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True
    )
    db.add(organizer)
    db.commit()
    db.refresh(organizer)
    
    deal = Deal(
        sponsor_id=test_user.id,
        organizer_id=organizer.id,
        deal_type="sponsorship",
        status="proposed",
        payment_amount=1000,
        currency="INR",
        sponsor_accepted=True
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal, organizer
