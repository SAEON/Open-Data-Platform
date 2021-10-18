from sqlalchemy import select

import migrate.initdb
from odp import ODPScope
from odp.db import Session
from odp.db.models import (
    Client,
    ClientScope,
    Collection,
    Project,
    Provider,
    Role,
    RoleScope,
    Scope,
    User,
    UserRole,
    Tag,
)
from test.factories import (
    ClientFactory,
    CollectionFactory,
    ProjectFactory,
    ProviderFactory,
    RoleFactory,
    ScopeFactory,
    UserFactory,
    TagFactory,
)


def test_db_setup():
    migrate.initdb.create_scopes(Session)
    Session.commit()
    result = Session.execute(select(Scope.id))
    assert result.scalars().all() == [s.value for s in ODPScope]

    ScopeFactory()  # create an arbitrary (external) scope, not for the sysadmin

    migrate.initdb.create_admin_role(Session)
    Session.commit()
    result = Session.execute(select(Role))
    assert result.scalar_one().id == migrate.initdb.ODP_ADMIN_ROLE

    result = Session.execute(select(RoleScope))
    assert [(row.role_id, row.scope_id) for row in result.scalars()] \
           == [(migrate.initdb.ODP_ADMIN_ROLE, s.value) for s in ODPScope]


def test_create_client():
    client = ClientFactory()
    result = Session.execute(select(Client))
    assert result.scalar_one().name == client.name


def test_create_client_with_scopes():
    scopes = ScopeFactory.create_batch(2)
    client = ClientFactory(scopes=scopes)
    result = Session.execute(select(ClientScope.client_id, ClientScope.scope_id))
    assert result.all() == [(client.id, scope.id) for scope in scopes]


def test_create_collection():
    collection = CollectionFactory()
    result = Session.execute(select(Collection))
    assert result.scalar_one().id == collection.id


def test_create_project():
    project = ProjectFactory()
    result = Session.execute(select(Project))
    assert result.scalar_one().id == project.id


def test_create_provider():
    provider = ProviderFactory()
    result = Session.execute(select(Provider))
    assert result.scalar_one().id == provider.id


def test_create_role():
    role = RoleFactory()
    result = Session.execute(select(Role))
    assert result.scalar_one().id == role.id


def test_create_role_with_scopes():
    scopes = ScopeFactory.create_batch(2)
    role = RoleFactory(scopes=scopes)
    result = Session.execute(select(RoleScope.role_id, RoleScope.scope_id))
    assert result.all() == [(role.id, scope.id) for scope in scopes]


def test_create_scope():
    scope = ScopeFactory()
    result = Session.execute(select(Scope))
    assert result.scalar_one().id == scope.id


def test_create_user():
    user = UserFactory()
    result = Session.execute(select(User))
    assert result.scalar_one().email == user.email


def test_create_user_with_roles():
    roles = RoleFactory.create_batch(2)
    user = UserFactory(roles=roles)
    result = Session.execute(select(UserRole.user_id, UserRole.role_id))
    assert result.all() == [(user.id, role.id) for role in roles]


def test_create_tag():
    tag = TagFactory()
    result = Session.execute(select(Tag))
    assert result.scalar_one().id == tag.id
