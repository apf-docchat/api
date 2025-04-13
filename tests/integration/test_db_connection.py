import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        pytest.skip("DATABASE_URI environment variable not set")

    engine = create_engine(database_uri)
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def test_db_connection(db_session):
    """Test that we can connect to the database."""
    try:
        result = db_session.execute(select(1))
        assert result.scalar() == 1
    except Exception as e:
        pytest.fail(f"Failed to connect to database: {str(e)}")
