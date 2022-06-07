from datetime import datetime, timezone
from random import randint

from fastapi import APIRouter, Depends, HTTPException
from jschon import JSON, JSONSchema
from sqlalchemy import func, select
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from odp import DOI_PREFIX, ODPScope
from odp.api.lib.auth import Authorize, Authorized, TagAuthorize, UntagAuthorize
from odp.api.lib.paging import Page, Paginator
from odp.api.lib.schema import get_tag_schema
from odp.api.lib.utils import output_tag_instance_model
from odp.api.models import CollectionModel, CollectionModelIn, TagInstanceModel, TagInstanceModelIn
from odp.db import Session
from odp.db.models import AuditCommand, Collection, CollectionTag, CollectionTagAudit, Record, Tag, TagType

router = APIRouter()


def output_collection_model(result) -> CollectionModel:
    return CollectionModel(
        id=result.Collection.id,
        name=result.Collection.name,
        doi_key=result.Collection.doi_key,
        provider_id=result.Collection.provider_id,
        project_ids=[project.id for project in result.Collection.projects],
        record_count=result.count,
        tags=[
            output_tag_instance_model(collection_tag)
            for collection_tag in result.Collection.tags
        ],
    )


@router.get(
    '/',
    response_model=Page[CollectionModel],
)
async def list_collections(
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_READ)),
        paginator: Paginator = Depends(),
):
    stmt = (
        select(Collection, func.count(Record.id)).
        outerjoin(Record).
        group_by(Collection)
    )
    if auth.provider_ids != '*':
        stmt = stmt.where(Collection.provider_id.in_(auth.provider_ids))

    return paginator.paginate(
        stmt,
        lambda row: output_collection_model(row),
        sort_model=Collection,
    )


@router.get(
    '/{collection_id}',
    response_model=CollectionModel,
)
async def get_collection(
        collection_id: str,
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_READ)),
):
    stmt = (
        select(Collection, func.count(Record.id)).
        outerjoin(Record).
        where(Collection.id == collection_id).
        group_by(Collection)
    )

    if not (result := Session.execute(stmt).one_or_none()):
        raise HTTPException(HTTP_404_NOT_FOUND)

    if auth.provider_ids != '*' and result.Collection.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    return output_collection_model(result)


@router.post(
    '/',
)
async def create_collection(
        collection_in: CollectionModelIn,
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_ADMIN)),
):
    if auth.provider_ids != '*' and collection_in.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    if Session.get(Collection, collection_in.id):
        raise HTTPException(HTTP_409_CONFLICT, 'Collection id is already in use')

    collection = Collection(
        id=collection_in.id,
        name=collection_in.name,
        doi_key=collection_in.doi_key,
        provider_id=collection_in.provider_id,
    )
    collection.save()


@router.put(
    '/',
)
async def update_collection(
        collection_in: CollectionModelIn,
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_ADMIN)),
):
    if auth.provider_ids != '*' and collection_in.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    if not (collection := Session.get(Collection, collection_in.id)):
        raise HTTPException(HTTP_404_NOT_FOUND)

    collection.name = collection_in.name
    collection.doi_key = collection_in.doi_key
    collection.provider_id = collection_in.provider_id
    collection.save()


@router.delete(
    '/{collection_id}',
)
async def delete_collection(
        collection_id: str,
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_ADMIN)),
):
    if not (collection := Session.get(Collection, collection_id)):
        raise HTTPException(HTTP_404_NOT_FOUND)

    if auth.provider_ids != '*' and collection.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    collection.delete()


@router.post(
    '/{collection_id}/tag',
    response_model=TagInstanceModel,
)
async def tag_collection(
        collection_id: str,
        tag_instance_in: TagInstanceModelIn,
        tag_schema: JSONSchema = Depends(get_tag_schema),
        auth: Authorized = Depends(TagAuthorize()),
):
    if not (collection := Session.get(Collection, collection_id)):
        raise HTTPException(HTTP_404_NOT_FOUND)

    if auth.provider_ids != '*' and collection.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    if collection_tag := Session.execute(
        select(CollectionTag).
        where(CollectionTag.collection_id == collection_id).
        where(CollectionTag.tag_id == tag_instance_in.tag_id).
        where(CollectionTag.user_id == auth.user_id)
    ).scalar_one_or_none():
        command = AuditCommand.update
    else:
        if Session.get(
                Tag, (tag_instance_in.tag_id, TagType.collection)
        ).flag and Session.execute(
                select(CollectionTag).
                where(CollectionTag.collection_id == collection_id).
                where(CollectionTag.tag_id == tag_instance_in.tag_id)
        ).first() is not None:
            raise HTTPException(HTTP_409_CONFLICT, 'Flag has already been set')

        collection_tag = CollectionTag(
            collection_id=collection_id,
            tag_id=tag_instance_in.tag_id,
            tag_type=TagType.collection,
            user_id=auth.user_id,
        )
        command = AuditCommand.insert

    if collection_tag.data != tag_instance_in.data:
        validity = tag_schema.evaluate(JSON(tag_instance_in.data)).output('detailed')
        if not validity['valid']:
            raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, validity)

        collection_tag.data = tag_instance_in.data
        collection_tag.timestamp = (timestamp := datetime.now(timezone.utc))
        collection_tag.save()

        CollectionTagAudit(
            client_id=auth.client_id,
            user_id=auth.user_id,
            command=command,
            timestamp=timestamp,
            _collection_id=collection_tag.collection_id,
            _tag_id=collection_tag.tag_id,
            _user_id=collection_tag.user_id,
            _data=collection_tag.data,
        ).save()

    return output_tag_instance_model(collection_tag)


@router.delete(
    '/{collection_id}/tag/{tag_id}',
)
async def untag_collection(
        collection_id: str,
        tag_id: str,
        auth: Authorized = Depends(UntagAuthorize()),
):
    if not (collection := Session.get(Collection, collection_id)):
        raise HTTPException(HTTP_404_NOT_FOUND)

    if auth.provider_ids != '*' and collection.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    if not (collection_tag := Session.execute(
        select(CollectionTag).
        where(CollectionTag.collection_id == collection_id).
        where(CollectionTag.tag_id == tag_id).
        where(CollectionTag.user_id == auth.user_id)
    ).scalar_one_or_none()):
        raise HTTPException(HTTP_404_NOT_FOUND)

    collection_tag.delete()

    CollectionTagAudit(
        client_id=auth.client_id,
        user_id=auth.user_id,
        command=AuditCommand.delete,
        timestamp=datetime.now(timezone.utc),
        _collection_id=collection_tag.collection_id,
        _tag_id=collection_tag.tag_id,
        _user_id=collection_tag.user_id,
    ).save()


@router.get(
    '/{collection_id}/doi/new',
    response_model=str,
)
async def get_new_doi(
        collection_id: str,
        auth: Authorized = Depends(Authorize(ODPScope.COLLECTION_READ)),
):
    if not (collection := Session.get(Collection, collection_id)):
        raise HTTPException(HTTP_404_NOT_FOUND)

    if auth.provider_ids != '*' and collection.provider_id not in auth.provider_ids:
        raise HTTPException(HTTP_403_FORBIDDEN)

    if not (doi_key := collection.doi_key):
        raise HTTPException(HTTP_422_UNPROCESSABLE_ENTITY, 'The collection does not have a DOI key')

    while True:
        num = randint(0, 99999999)
        doi = f'{DOI_PREFIX}/{doi_key}.{num:08}'
        if Session.execute(select(Record).where(Record.doi == doi)).first() is None:
            break

    return doi
