from sqlalchemy import select
from sqlalchemy.orm import defaultload

from source.common.flask_sqlachemy import db
from source.common.models.models import Collection, Module


def get_collection(collection_id: int) -> Collection:
    collection = db.session.execute(
        select(Collection).where(Collection.collection_id == collection_id).options(defaultload("*").noload())
    ).scalar_one_or_none()

    return collection


def get_collection_by_name(org_id: str, collection_name: str) -> Collection:
    collection = db.session.execute(
        select(Collection).where(Collection.org_id == org_id, Collection.collection_name == collection_name)
    ).scalar_one_or_none()
    return collection


# TODO: This should actuallly be a relationship in the Collection model
def get_module_name_for_collection(collection_id: str) -> str:
    module_name = db.session.execute(
        select(Module.name).where(Module.id == collection_id)
    ).scalar_one_or_none()

    return module_name
