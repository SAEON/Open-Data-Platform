from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func

from odp.api2.models import CollectionIn, CollectionOut, CollectionSort
from odp.api2.routers import Pager, Paging
from odp.db import Session
from odp.db.models import Collection, Record

router = APIRouter()


@router.get('/', response_model=List[CollectionOut])
async def list_collections(pager: Pager = Depends(Paging(CollectionSort))):
    stmt = (
        select(Collection, func.count(Record.id)).
        outerjoin(Record).
        group_by(Collection).
        order_by(getattr(Collection, pager.sort)).
        offset(pager.skip).
        limit(pager.limit)
    )

    collections = [
        CollectionOut(
            id=row.Collection.id,
            name=row.Collection.name,
            provider_id=row.Collection.provider.id,
            project_ids=[project.id for project in row.Collection.projects],
            record_count=row.count,
        )
        for row in Session.execute(stmt)
    ]

    return collections


@router.get('/{collection_id}', response_model=CollectionOut)
async def get_collection(
        collection_id: str,
):
    stmt = (
        select(Collection, func.count(Record.id)).
        outerjoin(Record).
        where(Collection.id == collection_id).
        group_by(Collection)
    )

    if not (result := Session.execute(stmt).one_or_none()):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return CollectionOut(
        id=result.Collection.id,
        name=result.Collection.name,
        provider_id=result.Collection.provider_id,
        project_ids=[project.id for project in result.Collection.projects],
        record_count=result.count,
    )


@router.put('/')
async def update_collection(
        collection_in: CollectionIn,
):
    if not (collection := Session.get(Collection, collection_in.id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    collection.name = collection_in.name
    collection.provider_id = collection_in.provider_id
    collection.save()


@router.delete('/{collection_id}')
async def delete_collection(
        collection_id: str,
):
    if not (collection := Session.get(Collection, collection_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    collection.delete()
