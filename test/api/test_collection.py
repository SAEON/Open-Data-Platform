from random import randint

import pytest
from sqlalchemy import select

from odp import ODPScope
from odp.db import Session
from odp.db.models import Collection
from test.api import assert_empty_result, assert_forbidden, all_scopes, all_scopes_excluding
from test.factories import CollectionFactory, ProjectFactory, ProviderFactory


@pytest.fixture
def collection_batch():
    """Create and commit a batch of Collection instances."""
    collections = [CollectionFactory() for _ in range(randint(3, 5))]
    ProjectFactory.create_batch(randint(0, 3), collections=collections)
    return collections


@pytest.fixture
def collection_batch_no_projects():
    """Create and commit a batch of Collection instances
    without projects, for testing the update API - we cannot
    assign projects to collections, only the other way around."""
    return [CollectionFactory() for _ in range(randint(3, 5))]


def collection_build(provider=None, **id):
    """Build and return an uncommitted Collection instance.
    Referenced provider is however committed."""
    return CollectionFactory.build(
        **id,
        provider=provider or (provider := ProviderFactory()),
        provider_id=provider.id,
    )


def project_ids(collection):
    return tuple(project.id for project in collection.projects)


def assert_db_state(collections):
    """Verify that the DB collection table contains the given collection batch."""
    Session.expire_all()
    result = Session.execute(select(Collection)).scalars().all()
    assert set((row.id, row.name, row.provider_id, project_ids(row)) for row in result) \
           == set((collection.id, collection.name, collection.provider_id, project_ids(collection)) for collection in collections)


def assert_json_result(response, json, collection):
    """Verify that the API result matches the given collection object."""
    assert response.status_code == 200
    assert json['id'] == collection.id
    assert json['name'] == collection.name
    assert json['provider_id'] == collection.provider_id
    assert tuple(json['project_ids']) == project_ids(collection)


def assert_json_results(response, json, collections):
    """Verify that the API result list matches the given collection batch."""
    json.sort(key=lambda j: j['id'])
    collections.sort(key=lambda c: c.id)
    for n, collection in enumerate(collections):
        assert_json_result(response, json[n], collection)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_READ], True),
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_READ, ODPScope.COLLECTION_ADMIN), False),
])
def test_list_collections(api, collection_batch, scopes, authorized):
    r = api(scopes).get('/collection/')
    if authorized:
        assert_json_results(r, r.json(), collection_batch)
    else:
        assert_forbidden(r)
    assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_READ], True),
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_READ, ODPScope.COLLECTION_ADMIN), False),
])
def test_list_collections_with_provider_specific_api_client(api, collection_batch, scopes, authorized):
    api_client_provider = collection_batch[2].provider
    r = api(scopes, api_client_provider).get('/collection/')
    if authorized:
        assert_json_results(r, r.json(), [collection_batch[2]])
    else:
        assert_forbidden(r)
    assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_READ], True),
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_READ, ODPScope.COLLECTION_ADMIN), False),
])
def test_get_collection(api, collection_batch, scopes, authorized):
    r = api(scopes).get(f'/collection/{collection_batch[2].id}')
    if authorized:
        assert_json_result(r, r.json(), collection_batch[2])
    else:
        assert_forbidden(r)
    assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, matching_provider, authorized', [
    ([ODPScope.COLLECTION_READ], True, True),
    ([ODPScope.COLLECTION_ADMIN], True, True),
    ([], True, False),
    (all_scopes, True, True),
    (all_scopes, False, False),
    (all_scopes_excluding(ODPScope.COLLECTION_READ, ODPScope.COLLECTION_ADMIN), True, False),
])
def test_get_collection_with_provider_specific_api_client(api, collection_batch, scopes, matching_provider, authorized):
    api_client_provider = collection_batch[2].provider if matching_provider else collection_batch[1].provider
    r = api(scopes, api_client_provider).get(f'/collection/{collection_batch[2].id}')
    if authorized:
        assert_json_result(r, r.json(), collection_batch[2])
    else:
        assert_forbidden(r)
    assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), False),
])
def test_create_collection(api, collection_batch, scopes, authorized):
    modified_collection_batch = collection_batch + [collection := collection_build()]
    r = api(scopes).post('/collection/', json=dict(
        id=collection.id,
        name=collection.name,
        provider_id=collection.provider_id,
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, matching_provider, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True, True),
    ([], True, False),
    (all_scopes, True, True),
    (all_scopes, False, False),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), True, False),
])
def test_create_collection_with_provider_specific_api_client(api, collection_batch, scopes, matching_provider, authorized):
    api_client_provider = collection_batch[2].provider if matching_provider else collection_batch[1].provider
    modified_collection_batch = collection_batch + [collection := collection_build(
        provider=collection_batch[2].provider
    )]
    r = api(scopes, api_client_provider).post('/collection/', json=dict(
        id=collection.id,
        name=collection.name,
        provider_id=collection.provider_id,
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), False),
])
def test_update_collection(api, collection_batch_no_projects, scopes, authorized):
    modified_collection_batch = collection_batch_no_projects.copy()
    modified_collection_batch[2] = (collection := collection_build(
        id=collection_batch_no_projects[2].id,
    ))
    r = api(scopes).put('/collection/', json=dict(
        id=collection.id,
        name=collection.name,
        provider_id=collection.provider_id,
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch_no_projects)


@pytest.mark.parametrize('scopes, matching_provider, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True, True),
    ([], True, False),
    (all_scopes, True, True),
    (all_scopes, False, False),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), True, False),
])
def test_update_collection_with_provider_specific_api_client(api, collection_batch_no_projects, scopes, matching_provider, authorized):
    api_client_provider = collection_batch_no_projects[2].provider if matching_provider else collection_batch_no_projects[1].provider
    modified_collection_batch = collection_batch_no_projects.copy()
    modified_collection_batch[2] = (collection := collection_build(
        id=collection_batch_no_projects[2].id,
        provider=collection_batch_no_projects[2].provider,
    ))
    r = api(scopes, api_client_provider).put('/collection/', json=dict(
        id=collection.id,
        name=collection.name,
        provider_id=collection.provider_id,
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch_no_projects)


@pytest.mark.parametrize('scopes, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True),
    ([], False),
    (all_scopes, True),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), False),
])
def test_delete_collection(api, collection_batch, scopes, authorized):
    modified_collection_batch = collection_batch.copy()
    del modified_collection_batch[2]
    r = api(scopes).delete(f'/collection/{collection_batch[2].id}')
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch)


@pytest.mark.parametrize('scopes, matching_provider, authorized', [
    ([ODPScope.COLLECTION_ADMIN], True, True),
    ([], True, False),
    (all_scopes, True, True),
    (all_scopes, False, False),
    (all_scopes_excluding(ODPScope.COLLECTION_ADMIN), True, False),
])
def test_delete_collection_with_provider_specific_api_client(api, collection_batch, scopes, matching_provider, authorized):
    api_client_provider = collection_batch[2].provider if matching_provider else collection_batch[1].provider
    modified_collection_batch = collection_batch.copy()
    del modified_collection_batch[2]
    r = api(scopes, api_client_provider).delete(f'/collection/{collection_batch[2].id}')
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_collection_batch)
    else:
        assert_forbidden(r)
        assert_db_state(collection_batch)
