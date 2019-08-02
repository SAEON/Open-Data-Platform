from typing import List
from fastapi import APIRouter, Depends

from odpapi.lib.common import PagerParams
from odpapi.lib.adapters import ODPAPIAdapter, get_adapter
from odpapi.models.institution import Institution, InstitutionIn, InstitutionOut
from odpapi.lib.security import HydraAuth

router = APIRouter()


@router.get('/', response_model=List[Institution])
async def list_institutions(
        pager: PagerParams = Depends(),
        adapter: ODPAPIAdapter = Depends(get_adapter),
        access_token: str = Depends(HydraAuth(['odp.institutions.view'])),
):
    return adapter.list_institutions(pager, access_token)


@router.get('/{id_or_name}', response_model=Institution)
async def get_institution(
        id_or_name: str,
        adapter: ODPAPIAdapter = Depends(get_adapter),
        access_token: str = Depends(HydraAuth(['odp.institutions.view'])),
):
    return adapter.get_institution(id_or_name, access_token)


@router.post('/', response_model=InstitutionOut)
async def add_institution(
        institution: InstitutionIn,
        adapter: ODPAPIAdapter = Depends(get_adapter),
        access_token: str = Depends(HydraAuth(['odp.institutions.add'])),
):
    return adapter.add_institution(institution, access_token)


@router.put('/{id_or_name}', response_model=InstitutionOut)
async def update_institution(
        id_or_name: str,
        institution: InstitutionIn,
        adapter: ODPAPIAdapter = Depends(get_adapter),
        access_token: str = Depends(HydraAuth(['odp.institutions.manage'])),
):
    return adapter.update_institution(id_or_name, institution, access_token)


@router.delete('/{id_or_name}', response_model=bool)
async def delete_institution(
        id_or_name: str,
        adapter: ODPAPIAdapter = Depends(get_adapter),
        access_token: str = Depends(HydraAuth(['odp.institutions.manage'])),
):
    return adapter.delete_institution(id_or_name, access_token)
