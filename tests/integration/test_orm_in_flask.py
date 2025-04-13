import pytest
from sqlalchemy import select

from source.api.app_factory import create_app
from source.common.flask_sqlachemy import db


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    app = create_app()

    app.config.update({
        "TESTING": True,
    })

    yield app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


def test_orm_connection(app):
    """Test that we can connect to the database and perform basic operations."""
    with app.app_context():
        # Verify we can execute a simple query
        result = db.session.execute(select(1)).scalar()
        assert result == 1


def test_user_queries(app):
    """Test that we can query the User model."""
    with app.app_context():
        from source.common.models.models import User
        from sqlalchemy import select

        # Test simple select
        result = db.session.execute(select(User)).all()
        assert isinstance(result, list)

        # Test select with filter
        result = db.session.execute(
            select(User).filter(User.is_admin == True)
        ).all()
        assert isinstance(result, list)


def test_organization_queries(app):
    """Test that we can query the Organization model."""
    with app.app_context():
        from source.common.models.models import Organization, OrganizationStatus
        from sqlalchemy import select

        # Test simple select
        result = db.session.execute(select(Organization)).all()
        assert isinstance(result, list)

        # Test select with filter
        result = db.session.execute(
            select(Organization).filter(Organization.status == OrganizationStatus.ACTIVE)
        ).all()
        assert isinstance(result, list)


def test_user_organization_relationship(app):
    """Test that we can query the User-Organization relationship."""
    with app.app_context():
        from source.common.models.models import UserOrganization, UserOrganizationRole
        from sqlalchemy import select

        # Test simple select
        result = db.session.execute(select(UserOrganization)).all()
        assert isinstance(result, list)

        # Test select with role filter
        result = db.session.execute(
            select(UserOrganization).filter(UserOrganization.role == UserOrganizationRole.ADMIN)
        ).all()
        assert isinstance(result, list)
