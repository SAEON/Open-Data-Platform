from random import randint

import pytest
from sqlalchemy import select

from odp import ODPScope
from odp.db import Session
from odp.db.models import Client
from odp.lib.hydra import TokenEndpointAuthMethod
from test.api import ProviderAuth, all_scopes, all_scopes_excluding, assert_empty_result, assert_forbidden
from test.factories import ClientFactory, ProviderFactory, ScopeFactory, fake


@pytest.fixture
def client_batch(hydra_admin_api):
    """Create and commit a batch of Client instances, and create
    an OAuth2 client config on Hydra for each."""
    clients = []
    for n in range(randint(3, 5)):
        clients += [client := ClientFactory(
            scopes=(scopes := ScopeFactory.create_batch(randint(1, 3))),
            is_provider_client=n in (1, 2) or randint(0, 1),
        )]
        hydra_admin_api.create_or_update_client(
            client.id,
            name=fake.catch_phrase(),
            secret=fake.password(),
            scope_ids=[s.id for s in scopes],
            grant_types=[],
        )

    return clients


@pytest.fixture(autouse=True)
def delete_hydra_clients(hydra_admin_api):
    """Delete Hydra client configs after each test."""
    try:
        yield
    finally:
        for hydra_client in hydra_admin_api.list_clients():
            if hydra_client.id != 'odp.test':
                hydra_admin_api.delete_client(hydra_client.id)


def client_build(provider=None, **id):
    """Build and return an uncommitted Client instance.
    Referenced scopes and/or provider are however committed."""
    return ClientFactory.build(
        **id,
        scopes=ScopeFactory.create_batch(randint(1, 3)),
        provider=provider or (provider := ProviderFactory() if randint(0, 1) else None),
        provider_id=provider.id if provider else None,
    )


def scope_ids(client):
    return tuple(sorted(scope.id for scope in client.scopes))


def assert_db_state(clients):
    """Verify that the DB client table contains the given client batch."""
    Session.expire_all()
    result = Session.execute(select(Client).where(Client.id != 'odp.test')).scalars().all()
    assert set((row.id, scope_ids(row), row.provider_id) for row in result) \
           == set((client.id, scope_ids(client), client.provider_id) for client in clients)


def assert_json_result(response, json, client):
    """Verify that the API result matches the given client object.

    TODO: test Hydra client config values
    """
    assert response.status_code == 200
    assert json['id'] == client.id
    assert json['provider_id'] == client.provider_id
    assert tuple(sorted(json['scope_ids'])) == scope_ids(client)


def assert_json_results(response, json, clients):
    """Verify that the API result list matches the given client batch."""
    items = [j for j in json['items'] if j['id'] != 'odp.test']
    assert json['total'] - 1 == len(items) == len(clients)
    items.sort(key=lambda i: i['id'])
    clients.sort(key=lambda c: c.id)
    for n, client in enumerate(clients):
        assert_json_result(response, items[n], client)


@pytest.mark.parametrize('scopes', [
    [ODPScope.CLIENT_READ],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.CLIENT_READ),
])
def test_list_clients(api, client_batch, scopes, provider_auth):
    authorized = ODPScope.CLIENT_READ in scopes

    if provider_auth == ProviderAuth.MATCH:
        api_client_provider = client_batch[2].provider
        expected_result_batch = [client_batch[2]]
    elif provider_auth == ProviderAuth.MISMATCH:
        api_client_provider = ProviderFactory()
        expected_result_batch = []
    else:
        api_client_provider = None
        expected_result_batch = client_batch

    r = api(scopes, api_client_provider).get('/client/')

    if authorized:
        assert_json_results(r, r.json(), expected_result_batch)
    else:
        assert_forbidden(r)

    assert_db_state(client_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.CLIENT_READ],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.CLIENT_READ),
])
def test_get_client(api, client_batch, scopes, provider_auth):
    authorized = ODPScope.CLIENT_READ in scopes and \
                 provider_auth in (ProviderAuth.NONE, ProviderAuth.MATCH)

    if provider_auth == ProviderAuth.MATCH:
        api_client_provider = client_batch[2].provider
    elif provider_auth == ProviderAuth.MISMATCH:
        api_client_provider = client_batch[1].provider
    else:
        api_client_provider = None

    r = api(scopes, api_client_provider).get(f'/client/{client_batch[2].id}')

    if authorized:
        assert_json_result(r, r.json(), client_batch[2])
    else:
        assert_forbidden(r)

    assert_db_state(client_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.CLIENT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.CLIENT_ADMIN),
])
def test_create_client(api, client_batch, scopes, provider_auth):
    authorized = ODPScope.CLIENT_ADMIN in scopes and \
                 provider_auth in (ProviderAuth.NONE, ProviderAuth.MATCH)

    if provider_auth == ProviderAuth.MATCH:
        api_client_provider = client_batch[2].provider
    elif provider_auth == ProviderAuth.MISMATCH:
        api_client_provider = client_batch[1].provider
    else:
        api_client_provider = None

    if provider_auth in (ProviderAuth.MATCH, ProviderAuth.MISMATCH):
        new_client_provider = client_batch[2].provider
    else:
        new_client_provider = None

    modified_client_batch = client_batch + [client := client_build(
        provider=new_client_provider
    )]

    r = api(scopes, api_client_provider).post('/client/', json=dict(
        id=client.id,
        name=fake.catch_phrase(),
        secret=fake.password(),
        scope_ids=scope_ids(client),
        provider_id=client.provider_id,
        grant_types=[],
        response_types=[],
        redirect_uris=[],
        post_logout_redirect_uris=[],
        token_endpoint_auth_method=TokenEndpointAuthMethod.CLIENT_SECRET_BASIC,
        allowed_cors_origins=[],
    ))

    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_client_batch)
    else:
        assert_forbidden(r)
        assert_db_state(client_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.CLIENT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.CLIENT_ADMIN),
])
def test_update_client(api, client_batch, scopes, provider_auth):
    authorized = ODPScope.CLIENT_ADMIN in scopes and \
                 provider_auth in (ProviderAuth.NONE, ProviderAuth.MATCH)

    if provider_auth == ProviderAuth.MATCH:
        api_client_provider = client_batch[2].provider
    elif provider_auth == ProviderAuth.MISMATCH:
        api_client_provider = client_batch[1].provider
    else:
        api_client_provider = None

    if provider_auth in (ProviderAuth.MATCH, ProviderAuth.MISMATCH):
        modified_client_provider = client_batch[2].provider
    else:
        modified_client_provider = None

    modified_client_batch = client_batch.copy()
    modified_client_batch[2] = (client := client_build(
        id=client_batch[2].id,
        provider=modified_client_provider,
    ))

    r = api(scopes, api_client_provider).put('/client/', json=dict(
        id=client.id,
        name=fake.catch_phrase(),
        secret=fake.password(),
        scope_ids=scope_ids(client),
        provider_id=client.provider_id,
        grant_types=[],
        response_types=[],
        redirect_uris=[],
        post_logout_redirect_uris=[],
        token_endpoint_auth_method=TokenEndpointAuthMethod.CLIENT_SECRET_BASIC,
        allowed_cors_origins=[],
    ))

    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_client_batch)
    else:
        assert_forbidden(r)
        assert_db_state(client_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.CLIENT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.CLIENT_ADMIN),
])
def test_delete_client(api, client_batch, scopes, provider_auth):
    authorized = ODPScope.CLIENT_ADMIN in scopes and \
                 provider_auth in (ProviderAuth.NONE, ProviderAuth.MATCH)

    if provider_auth == ProviderAuth.MATCH:
        api_client_provider = client_batch[2].provider
    elif provider_auth == ProviderAuth.MISMATCH:
        api_client_provider = client_batch[1].provider
    else:
        api_client_provider = None

    modified_client_batch = client_batch.copy()
    del modified_client_batch[2]

    r = api(scopes, api_client_provider).delete(f'/client/{client_batch[2].id}')

    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_client_batch)
    else:
        assert_forbidden(r)
        assert_db_state(client_batch)
