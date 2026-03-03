from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
from .logger import logger

DATABASE_URL = settings.DATABASE_URL
# Redact password for security in logs
redacted_url = DATABASE_URL
if "@" in DATABASE_URL:
    try:
        prefix, rest = DATABASE_URL.split("://", 1)
        auth, host = rest.split("@", 1)
        if ":" in auth:
            user, _ = auth.split(":", 1)
            redacted_url = f"{prefix}://{user}:****@{host}"
    except Exception:
        pass

logger.info(f"Connecting to database: {redacted_url}")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
