"""ORM Fixes

Revision ID: b620c013267c
Revises: 712af525a5ab
Create Date: 2024-12-17 01:09:53.809498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b620c013267c'
down_revision: Union[str, None] = '712af525a5ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('unique_file_id_and_schema_id', table_name='docchat_metadata')
    op.drop_index('collection_id', table_name='docchat_metadata_schema')
    op.drop_index('schema_id_UNIQUE', table_name='docchat_metadata_schema')
    op.create_unique_constraint(op.f('uq_docchat_metadata_schema_collection_id_field'), 'docchat_metadata_schema', ['collection_id', 'field'])
    op.create_unique_constraint(op.f('uq_docchat_metadata_schema_collection_id_order_number'), 'docchat_metadata_schema', ['collection_id', 'order_number'])
    op.drop_index('org_id', table_name='docguide_sections_learned_status')
    op.drop_index('type', table_name='entity_configurations')
    op.create_unique_constraint(op.f('uq_entity_configurations_type'), 'entity_configurations', ['type'])
    op.create_index(op.f('ix_username'), 'log_ai_calls', ['username'], unique=False)
    op.drop_index('idx_name', table_name='modules')
    op.create_unique_constraint(op.f('uq_modules_name'), 'modules', ['name'])
    op.drop_index('org_name', table_name='organization')
    op.create_unique_constraint(op.f('uq_organization_org_name'), 'organization', ['org_name'])
    op.create_unique_constraint(op.f('uq_organization_collections_org_id_collection_id'), 'organization_collections', ['org_id', 'collection_id'])
    op.drop_index('idx_role_name', table_name='user_roles')
    op.drop_index('idx_user_id', table_name='user_roles')
    op.create_index('ix_user_roles_user_id_role_name', 'user_roles', ['user_id', 'role_name'], unique=False)
    op.drop_index('email', table_name='users')
    op.drop_index('username', table_name='users')
    op.create_unique_constraint(op.f('uq_users_email'), 'users', ['email'])
    op.create_unique_constraint(op.f('uq_users_username'), 'users', ['username'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('uq_users_username'), 'users', type_='unique')
    op.drop_constraint(op.f('uq_users_email'), 'users', type_='unique')
    op.create_index('username', 'users', ['username'], unique=True)
    op.create_index('email', 'users', ['email'], unique=True)
    op.drop_index('ix_user_roles_user_id_role_name', table_name='user_roles')
    op.create_index('idx_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('idx_role_name', 'user_roles', ['role_name'], unique=False)
    op.drop_constraint(op.f('uq_organization_collections_org_id_collection_id'), 'organization_collections', type_='unique')
    op.drop_constraint(op.f('uq_organization_org_name'), 'organization', type_='unique')
    op.create_index('org_name', 'organization', ['org_name'], unique=True)
    op.drop_constraint(op.f('uq_modules_name'), 'modules', type_='unique')
    op.create_index('idx_name', 'modules', ['name'], unique=True)
    op.drop_index(op.f('ix_username'), table_name='log_ai_calls')
    op.drop_constraint(op.f('uq_entity_configurations_type'), 'entity_configurations', type_='unique')
    op.create_index('type', 'entity_configurations', ['type'], unique=True)
    op.create_index('org_id', 'docguide_sections_learned_status', ['org_id', 'user_id', 'section_id'], unique=True)
    op.drop_constraint(op.f('uq_docchat_metadata_schema_collection_id_order_number'), 'docchat_metadata_schema', type_='unique')
    op.drop_constraint(op.f('uq_docchat_metadata_schema_collection_id_field'), 'docchat_metadata_schema', type_='unique')
    op.create_index('schema_id_UNIQUE', 'docchat_metadata_schema', ['schema_id'], unique=True)
    op.create_index('collection_id', 'docchat_metadata_schema', ['collection_id', 'field'], unique=True)
    op.create_index('unique_file_id_and_schema_id', 'docchat_metadata', ['file_id', 'schema_id'], unique=True)
    # ### end Alembic commands ###
