from sqlalchemy import select
from sqlalchemy.orm import Session

from source.common.models.models import Organization


def get_org_slug_by_id(db_session: Session, org_id: str) -> str | None:
    with db_session:
        stmt = select(Organization.org_name).where(Organization.org_id == org_id)
        result = db_session.execute(stmt).first()

    return result


def get_org_id_by_slug(db_session: Session, org_slug: str) -> int | None:
    with db_session:
        stmt = select(Organization.org_id).where(Organization.org_name == org_slug)
        result = db_session.execute(stmt).first()

    return result
