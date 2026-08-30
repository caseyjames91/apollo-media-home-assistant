from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base
from app.db.migrations import migrate_database

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    from app import models  # noqa: F401

    # Upgrade tables carried forward from pre-0.2 releases before asking
    # SQLAlchemy to reconcile the rest of the metadata.  create_all() alone
    # never alters an existing SQLite table, which is why 0.2.0 could start
    # but fail as soon as an ORM query selected a new column.
    migrate_database(engine)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
