# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from app.core.config import settings

# Fix driver for SQLAlchemy to use psycopg2
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Create SQLAlchemy engine
# pool_pre_ping ensures connections aren't stale
engine = create_engine(db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator:
    """
    Dependency function to yield a database session for FastAPI routes.
    Ensures the connection is closed after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()