from enum import Enum

__version__ = '2.0.0'

DOI_PREFIX = 10.15493


class ODPScope(str, Enum):
    # catalog
    CATALOG_READ = 'odp.catalog:read'

    # client
    CLIENT_ADMIN = 'odp.client:admin'
    CLIENT_READ = 'odp.client:read'

    # collection
    COLLECTION_ADMIN = 'odp.collection:admin'
    COLLECTION_READ = 'odp.collection:read'
    COLLECTION_FLAG_ARCHIVE = 'odp.collection_flag:archive'
    COLLECTION_FLAG_PUBLISH = 'odp.collection_flag:publish'

    # flag
    FLAG_READ = 'odp.flag:read'

    # project
    PROJECT_ADMIN = 'odp.project:admin'
    PROJECT_READ = 'odp.project:read'

    # provider
    PROVIDER_ADMIN = 'odp.provider:admin'
    PROVIDER_READ = 'odp.provider:read'

    # record
    RECORD_ADMIN = 'odp.record:admin'
    RECORD_READ = 'odp.record:read'
    RECORD_WRITE = 'odp.record:write'
    RECORD_TAG_QC = 'odp.record_tag:qc'
    RECORD_FLAG_MIGRATED = 'odp.record_flag:migrated'

    # role
    ROLE_ADMIN = 'odp.role:admin'
    ROLE_READ = 'odp.role:read'

    # schema
    SCHEMA_READ = 'odp.schema:read'

    # scope
    SCOPE_READ = 'odp.scope:read'

    # tag
    TAG_READ = 'odp.tag:read'

    # user
    USER_ADMIN = 'odp.user:admin'
    USER_READ = 'odp.user:read'


class ODPCollectionFlag(str, Enum):
    ARCHIVE = 'collection-archive'
    PUBLISH = 'collection-publish'


class ODPRecordFlag(str, Enum):
    MIGRATED = 'record-migrated'


class ODPRecordTag(str, Enum):
    QC = 'record-qc'
