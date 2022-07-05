from random import randint

import pytest
from sqlalchemy import select

from odp import ODPScope
from odp.db import Session
from odp.db.models import Project
from test.api import all_scopes, all_scopes_excluding, assert_conflict, assert_empty_result, assert_forbidden, assert_not_found
from test.factories import CollectionFactory, ProjectFactory


@pytest.fixture
def project_batch():
    """Create and commit a batch of Project instances."""
    return [
        ProjectFactory(collections=CollectionFactory.create_batch(randint(0, 3)))
        for _ in range(randint(3, 5))
    ]


def project_build(**id):
    """Build and return an uncommitted Project instance.
    Referenced collections are however committed."""
    return ProjectFactory.build(
        **id,
        collections=CollectionFactory.create_batch(randint(0, 3)),
    )


def collection_ids(project):
    return tuple(sorted(collection.id for collection in project.collections))


def assert_db_state(projects):
    """Verify that the DB project table contains the given project batch."""
    Session.expire_all()
    result = Session.execute(select(Project)).scalars().all()
    assert set((row.id, row.name, collection_ids(row)) for row in result) \
           == set((project.id, project.name, collection_ids(project)) for project in projects)


def assert_json_result(response, json, project):
    """Verify that the API result matches the given project object."""
    assert response.status_code == 200
    assert json['id'] == project.id
    assert json['name'] == project.name
    assert tuple(sorted(json['collection_ids'])) == collection_ids(project)


def assert_json_results(response, json, projects):
    """Verify that the API result list matches the given project batch."""
    items = json['items']
    assert json['total'] == len(items) == len(projects)
    items.sort(key=lambda i: i['id'])
    projects.sort(key=lambda p: p.id)
    for n, project in enumerate(projects):
        assert_json_result(response, items[n], project)


@pytest.mark.parametrize('scopes', [
    [ODPScope.PROJECT_READ],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.PROJECT_READ),
])
def test_list_projects(api, project_batch, scopes):
    authorized = ODPScope.PROJECT_READ in scopes
    r = api(scopes).get('/project/')
    if authorized:
        assert_json_results(r, r.json(), project_batch)
    else:
        assert_forbidden(r)
    assert_db_state(project_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.PROJECT_READ],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.PROJECT_READ),
])
def test_get_project(api, project_batch, scopes):
    authorized = ODPScope.PROJECT_READ in scopes
    r = api(scopes).get(f'/project/{project_batch[2].id}')
    if authorized:
        assert_json_result(r, r.json(), project_batch[2])
    else:
        assert_forbidden(r)
    assert_db_state(project_batch)


def test_get_project_not_found(api, project_batch):
    scopes = [ODPScope.PROJECT_READ]
    r = api(scopes).get('/project/foo')
    assert_not_found(r)
    assert_db_state(project_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.PROJECT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.PROJECT_ADMIN),
])
def test_create_project(api, project_batch, scopes):
    authorized = ODPScope.PROJECT_ADMIN in scopes
    modified_project_batch = project_batch + [project := project_build()]
    r = api(scopes).post('/project/', json=dict(
        id=project.id,
        name=project.name,
        collection_ids=collection_ids(project),
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_project_batch)
    else:
        assert_forbidden(r)
        assert_db_state(project_batch)


def test_create_project_conflict(api, project_batch):
    scopes = [ODPScope.PROJECT_ADMIN]
    project = project_build(id=project_batch[2].id)
    r = api(scopes).post('/project/', json=dict(
        id=project.id,
        name=project.name,
        collection_ids=collection_ids(project),
    ))
    assert_conflict(r, 'Project id is already in use')
    assert_db_state(project_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.PROJECT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.PROJECT_ADMIN),
])
def test_update_project(api, project_batch, scopes):
    authorized = ODPScope.PROJECT_ADMIN in scopes
    modified_project_batch = project_batch.copy()
    modified_project_batch[2] = (project := project_build(id=project_batch[2].id))
    r = api(scopes).put('/project/', json=dict(
        id=project.id,
        name=project.name,
        collection_ids=collection_ids(project),
    ))
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_project_batch)
    else:
        assert_forbidden(r)
        assert_db_state(project_batch)


def test_update_project_not_found(api, project_batch):
    scopes = [ODPScope.PROJECT_ADMIN]
    project = project_build(id='foo')
    r = api(scopes).put('/project/', json=dict(
        id=project.id,
        name=project.name,
        collection_ids=collection_ids(project),
    ))
    assert_not_found(r)
    assert_db_state(project_batch)


@pytest.mark.parametrize('scopes', [
    [ODPScope.PROJECT_ADMIN],
    [],
    all_scopes,
    all_scopes_excluding(ODPScope.PROJECT_ADMIN),
])
def test_delete_project(api, project_batch, scopes):
    authorized = ODPScope.PROJECT_ADMIN in scopes
    modified_project_batch = project_batch.copy()
    del modified_project_batch[2]
    r = api(scopes).delete(f'/project/{project_batch[2].id}')
    if authorized:
        assert_empty_result(r)
        assert_db_state(modified_project_batch)
    else:
        assert_forbidden(r)
        assert_db_state(project_batch)


def test_delete_project_not_found(api, project_batch):
    scopes = [ODPScope.PROJECT_ADMIN]
    r = api(scopes).delete('/project/foo')
    assert_not_found(r)
    assert_db_state(project_batch)
