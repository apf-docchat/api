import datetime
import enum
from typing import List, Optional

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Enum, Float, Index, Integer, \
    JSON, MetaData, String, TIMESTAMP, Text, func, Boolean, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship
from sqlalchemy.sql import expression


naming_convention = {
  "ix": "ix_%(column_0_N_name)s",
  "uq": "uq_%(table_name)s_%(column_0_N_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase, MappedAsDataclass):
    metadata = MetaData(naming_convention=naming_convention)

class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[datetime.date]] = mapped_column(Date)
    date_joined: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    last_login: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=expression.true())
    is_admin: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=expression.false())
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(190))
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))

    # organizations: Mapped[List['Organization']] = relationship('Organization', secondary='user_organization', back_populates='users', cascade='all')

    roles_current: Mapped[List['UserRoleCurrent']] = relationship('UserRoleCurrent', back_populates='user', cascade='all, delete-orphan')
    roles_history: Mapped[List['UserRoleHistory']] = relationship('UserRoleHistory', back_populates='user', cascade='all, delete-orphan')

    __tablename__ = 'users'


class UserRole(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    role_name: Mapped[str] = mapped_column(String(100))
    details: Mapped[Optional[str]] = mapped_column(String(300))
    objectives: Mapped[Optional[str]] = mapped_column(String(300))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_onupdate=func.now())
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=expression.true())

    roles_current: Mapped[List['UserRoleCurrent']] = relationship('UserRoleCurrent', back_populates='user_role', cascade='all, delete-orphan')
    roles_history: Mapped[List['UserRoleHistory']] = relationship('UserRoleHistory', back_populates='user_role', cascade='all, delete-orphan')

    __tablename__ = 'user_roles'

    __table_args__ = (
        Index('ix_user_roles_user_id_role_name', 'user_id', 'role_name'),
    )


class UserRoleCurrent(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    user_role_id: Mapped[int] = mapped_column(Integer, ForeignKey('user_roles.id'))
    selected_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_default=func.now())
    is_primary: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=expression.false())

    user: Mapped['User'] = relationship('User', back_populates='roles_current')
    user_role: Mapped['UserRole'] = relationship('UserRole', back_populates='roles_current')

    __tablename__ = 'user_role_current'


class UserRoleHistory(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    user_role_id: Mapped[int] = mapped_column(Integer, ForeignKey('user_roles.id'))
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_default=func.now())
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)

    user: Mapped['User'] = relationship('User', back_populates='roles_history')
    user_role: Mapped['UserRole'] = relationship('UserRole', back_populates='roles_history')

    __tablename__ = 'user_role_history'

class OrganizationStatus(enum.Enum):
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    SUSPENDED = 'SUSPENDED'

class Organization(Base):
    org_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_name: Mapped[str] = mapped_column(String(100), unique=True)
    creation_date: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_date: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_onupdate=func.now())
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    admin_user_id: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(Enum(OrganizationStatus), server_default=OrganizationStatus.ACTIVE.value)
    logo_url: Mapped[Optional[str]] = mapped_column(String(190))
    home_module_function_name: Mapped[Optional[str]] = mapped_column(String(100))
    vector_provider: Mapped[Optional[str]] = mapped_column(String(100))

    modules: Mapped[List['OrganizationModule']] = relationship('OrganizationModule', back_populates='org', cascade='all')
    # users: Mapped[List['User']] = relationship('User', secondary='user_organization', back_populates='organizations', cascade='all')
    collections: Mapped[List['Collection']] = relationship('Collection',
                                                           secondary='organization_collections',
                                                           back_populates='orgs',
                                                           cascade='all')
    # docchat_faq: Mapped[List['DocchatFaq']] = relationship('DocchatFaq', back_populates='organization', cascade='all')
    # docchat_metadata: Mapped[List['DocchatMetadata']] = relationship('DocchatMetadata', back_populates='organization', cascade='all')
    # docchat_metadata_schema: Mapped[List['DocchatMetadataSchema']] = relationship('DocchatMetadataSchema', back_populates='organization', cascade='all')
    # docguide_faq: Mapped[List['DocguideFaq']] = relationship('DocguideFaq', back_populates='organization', cascade='all')
    # docguide_file: Mapped[List['DocguideFile']] = relationship('DocguideFile', back_populates='organization', cascade='all')
    # docguide_section: Mapped[List['DocguideSection']] = relationship('DocguideSection', back_populates='organization', cascade='all')
    # docguide_sections_learned_status: Mapped[List['DocguideSectionsLearnedStatus']] = relationship('DocguideSectionsLearnedStatus', back_populates='organization', cascade='all')

    __tablename__ = 'organization'

class UserOrganizationRole(enum.Enum):
    MEMBER = 'MEMBER'
    ADMIN = 'ADMIN'
    GUEST = 'GUEST'
    SUPER_USER = 'SUPER_USER'

class UserOrganization(Base):
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(Enum(UserOrganizationRole), server_default=UserOrganizationRole.MEMBER.value)
    join_date: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # user: Mapped['User'] = relationship('User', back_populates='organizations')
    # organization: Mapped['Organization'] = relationship('Organization', back_populates='users')

    __tablename__ = 'user_organization'


class Module(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    button_text: Mapped[str] = mapped_column(String(150))
    description: Mapped[Optional[str]] = mapped_column(Text)
    form_action: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)

    __tablename__ = 'modules'


class OrganizationModule(Base):
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey('organization.org_id'), primary_key=True)
    module_id: Mapped[int] = mapped_column(Integer, ForeignKey('modules.id'), primary_key=True)
    subscribed_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    module: Mapped['Module'] = relationship('Module')
    org: Mapped['Organization'] = relationship('Organization', back_populates='modules')

    __tablename__ = 'organization_modules'


class SharingLevel(enum.Enum):
    ORG = 'ORG'
    PRIVATE = 'PRIVATE'
    LIMITED = 'LIMITED'

class Collection(Base):
    collection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    metatadata_prompt_prelude: Mapped[Optional[str]] = mapped_column(Text)
    metatadata_prompt: Mapped[Optional[str]] = mapped_column(Text)
    custom_instructions: Mapped[Optional[str]] = mapped_column(Text)
    org_id: Mapped[Optional[int]] = mapped_column(Integer)
    module_id: Mapped[Optional[int]] = mapped_column(Integer)
    collection_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    sharing_level: Mapped[str] = mapped_column(Enum(SharingLevel), server_default=SharingLevel.ORG.value)
    shared_with: Mapped[Optional[dict]] = mapped_column(JSON)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))

    orgs: Mapped[List['Organization']] = relationship('Organization', secondary='organization_collections',
                                                      back_populates='collections', cascade='all')
    files: Mapped[List['File']] = relationship('File', secondary='files_collections', back_populates='collections', cascade='all')
    owner: Mapped[Optional['User']] = relationship('User')

    # insights: Mapped[List['CollectionsInsight']] = relationship('CollectionsInsight', back_populates='collection', cascade='all')

    __tablename__ = 'collections'


class OrganizationCollections(Base):
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey('organization.org_id'), primary_key=True)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey('collections.collection_id'), primary_key=True)

    __tablename__ = 'organization_collections'

    __table_args__ = (
        UniqueConstraint('org_id', 'collection_id'),
    )


class DocchatFaq(Base):
    faq_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faq_question: Mapped[str] = mapped_column(Text)
    faq_answer: Mapped[str] = mapped_column(LONGTEXT)
    collection_id: Mapped[int] = mapped_column(Integer)
    org_id: Mapped[int] = mapped_column(Integer)

    # collection: Mapped['Collection'] = relationship('Collection', back_populates='docchat_faq')
    # organization: Mapped['Organization'] = relationship('Organization', back_populates='docchat_faq')

    __tablename__ = 'docchat_faq'


class DocchatMetadata(Base):
    org_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schema_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field: Mapped[str] = mapped_column(String(256), nullable=False)
    value: Mapped[str] = mapped_column(LONGTEXT, nullable=False)

    # organization: Mapped['Organization'] = relationship('Organization', back_populates='docchat_metadata')
    # collection: Mapped['Collection'] = relationship('Collection', back_populates='docchat_metadata')
    # file: Mapped['File'] = relationship('File', back_populates='docchat_metadata')
    # schema: Mapped['DocchatMetadataSchema'] = relationship('DocchatMetadataSchema', back_populates='docchat_metadata')

    __tablename__ = 'docchat_metadata'


class DocchatMetadataSchema(Base):
    schema_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(Integer)
    collection_id: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    order_number: Mapped[int] = mapped_column(Integer)

    # organization: Mapped['Organization'] = relationship('Organization', back_populates='docchat_metadata_schema')
    # collection: Mapped['Collection'] = relationship('Collection', back_populates='docchat_metadata_schema')

    __tablename__ = 'docchat_metadata_schema'

    __table_args__ = (
        UniqueConstraint('collection_id', 'field'),
        UniqueConstraint('collection_id', 'order_number'),
    )


class DocguideFaq(Base):
    faq_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faq_title: Mapped[str] = mapped_column(String(256))
    faq_content: Mapped[str] = mapped_column(Text)
    file_id: Mapped[int] = mapped_column(Integer)
    org_id: Mapped[int] = mapped_column(Integer)

    # file: Mapped['File'] = relationship('File', back_populates='docguide_faq')
    # organization: Mapped['Organization'] = relationship('Organization', back_populates='docguide_faq')

    __tablename__ = 'docguide_faq'


class DocguideFile(Base):
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(255))
    org_id: Mapped[int] = mapped_column(Integer)
    upload_date: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    doc_file_id: Mapped[int] = mapped_column(Integer)

    # docguide_sessions: Mapped[List['DocguideSession']] = relationship('DocguideSession', back_populates='file')

    __tablename__ = 'docguide_files'


class DocguideSection(Base):
    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_title: Mapped[str] = mapped_column(String(64))
    section_content: Mapped[str] = mapped_column(Text)
    order_number: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[int] = mapped_column(Integer)
    org_id: Mapped[int] = mapped_column(Integer)

    # docguide_sessions: Mapped[List['DocguideSession']] = relationship('DocguideSession', back_populates='section')
    # file: Mapped['DocguideFile'] = relationship('DocguideFile', back_populates='sections')
    # learned_status: Mapped[List['DocguideSectionsLearnedStatus']] = relationship('DocguideSectionsLearnedStatus', back_populates='section', cascade='all, delete-orphan')

    __tablename__ = 'docguide_sections'


class DocguideSectionsLearnedStatusOptions(enum.Enum):
    INITIAL = 'INITIAL'
    PARTIAL = 'PARTIAL'
    FULL = 'FULL'

class DocguideSectionsLearnedStatus(Base):
    org_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learned_status: Mapped[str] = mapped_column(Enum(DocguideSectionsLearnedStatusOptions), nullable=False)
    assessment_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))

    # organization: Mapped['Organization'] = relationship('Organization', back_populates='docguide_sections_learned_status')
    # user: Mapped['User'] = relationship('User', back_populates='docguide_sections_learned_status')
    # section: Mapped['DocguideSection'] = relationship('DocguideSection', back_populates='docguide_sections_learned_status')

    __tablename__ = 'docguide_sections_learned_status'



class Entity(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(String(50))
    data: Mapped[str] = mapped_column(LONGTEXT)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_onupdate=func.now())

    __tablename__ = 'entities'

    __table_args__ = (
        CheckConstraint('json_valid(`data`)', name='data_valid_json'),
    )


class EntityConfiguration(Base):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(String(50), unique=True)
    config: Mapped[str] = mapped_column(LONGTEXT)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_onupdate=func.now())

    __tablename__ = 'entity_configurations'

    __table_args__ = (
        CheckConstraint('json_valid(`config`)', name='config_valid_json'),
    )


class Job(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_onupdate=func.now())
    steps: Mapped[Optional[str]] = mapped_column(Text)
    order_number: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    creator_username: Mapped[Optional[str]] = mapped_column(String(50))
    updater_username: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=expression.true())
    org_id: Mapped[Optional[int]] = mapped_column(Integer)

    __tablename__ = 'jobs'


class LogAiCall(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp_start: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    username: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    user_content: Mapped[Optional[str]] = mapped_column(Text)
    system_content: Mapped[Optional[str]] = mapped_column(Text)
    response: Mapped[Optional[str]] = mapped_column(Text)
    timestamp_end: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)

    __tablename__ = 'log_ai_calls'


class Prompt(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_type: Mapped[str] = mapped_column(String(300))
    prompt_name: Mapped[str] = mapped_column(String(300))
    name_label: Mapped[str] = mapped_column(String(300))
    prompt_text: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    __tablename__ = 'prompts'


class PromptsArchive(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datetime_created: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    prompt_id: Mapped[int] = mapped_column(Integer)
    prompt_type: Mapped[str] = mapped_column(String(300))
    prompt_name: Mapped[str] = mapped_column(String(300))
    name_label: Mapped[str] = mapped_column(String(300))
    prompt_text: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    __tablename__ = 'prompts_archive'


class CollectionsInsight(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(Integer)
    query: Mapped[Optional[str]] = mapped_column(String(200))
    script: Mapped[Optional[str]] = mapped_column(Text)
    order_number: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(45))

    # collection: Mapped['Collection'] = relationship('Collection', back_populates='insights')

    __tablename__ = 'collections_insights'


class File(Base):
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(255))
    upload_datetime: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime,
                                                                         server_default=func.now())
    collection_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('collections.collection_id'))

    collections: Mapped[List['Collection']] = relationship('Collection', secondary='files_collections',
                                                           back_populates='files', cascade='all')
    # file_metadata: Mapped[List['FilesMetadata']] = relationship('FilesMetadata', back_populates='file', cascade='all')
    # metadata_plus: Mapped[List['FilesMetadataPlus']] = relationship('FilesMetadataPlus', back_populates='file', cascade='all')
    bm25_terms: Mapped[List['FilesBm25Term']] = relationship('FilesBm25Term', back_populates='file', cascade='all')
    bm25_meta: Mapped['FilesBm25Meta'] = relationship('FilesBm25Meta', back_populates='file', cascade='all')
    pages: Mapped[List['FilesPage']] = relationship('FilesPage', back_populates='file', cascade='all')

    __tablename__ = 'files'

class FilesMetadata(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(300))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    summary_short: Mapped[Optional[str]] = mapped_column(String(500))
    summary_long: Mapped[Optional[str]] = mapped_column(String(4000))
    questions: Mapped[Optional[str]] = mapped_column(Text)
    sections: Mapped[Optional[str]] = mapped_column(Text)

    # file: Mapped['File'] = relationship('File', back_populates='metadata')

    __tablename__ = 'files_metadata'


class FilesMetadataPlus(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer)
    metadata_: Mapped[str] = mapped_column('metadata', Text)

    # file: Mapped['File'] = relationship('File', back_populates='metadata_plus')

    __tablename__ = 'files_metadata_plus'



class FilesCollections(Base):
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.file_id'), primary_key=True)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey('collections.collection_id'), primary_key=True)

    __tablename__ = 'files_collections'


class FilesBm25Meta(Base):
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.file_id'), primary_key=True)
    avg_doc_len: Mapped[float] = mapped_column(Float)

    file: Mapped['File'] = relationship('File', back_populates='bm25_meta')

    __tablename__ = 'files_bm25_meta'


class FilesBm25Term(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.file_id'))
    term: Mapped[str] = mapped_column(String(255))
    idf: Mapped[float] = mapped_column(Float)

    file: Mapped['File'] = relationship('File', back_populates='bm25_terms')

    __tablename__ = 'files_bm25_terms'


class FilesPage(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.file_id'))
    page_number: Mapped[int] = mapped_column(Integer)
    tokens: Mapped[str] = mapped_column(Text)

    file: Mapped['File'] = relationship('File', back_populates='pages')

    __tablename__ = 'files_pages'
