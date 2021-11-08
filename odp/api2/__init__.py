from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from jschon import create_catalog, URI

import odp
from odp.api2.routers import (
    client,
    collection,
    project,
    provider,
    record,
    role,
    scope,
    status,
    user,
)
from odp.config import config
from odp.db import Session

catalog = create_catalog('2020-12')
catalog.add_directory(URI('https://odp.saeon.ac.za/schema/'), Path(__file__).parent.parent.parent / 'schema')

app = FastAPI(
    title="ODP API",
    description="SAEON | Open Data Platform API",
    version=odp.__version__,
    root_path=config.ODP.API.PATH_PREFIX,
    docs_url='/interactive',
    redoc_url='/docs',
)

app.include_router(client.router, prefix='/client', tags=['Client'])
app.include_router(collection.router, prefix='/collection', tags=['Collection'])
app.include_router(project.router, prefix='/project', tags=['Project'])
app.include_router(provider.router, prefix='/provider', tags=['Provider'])
app.include_router(record.router, prefix='/record', tags=['Record'])
app.include_router(role.router, prefix='/role', tags=['Role'])
app.include_router(scope.router, prefix='/scope', tags=['Scope'])
app.include_router(status.router, prefix='/status', tags=['Status'])
app.include_router(user.router, prefix='/user', tags=['User'])

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ODP.API.ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware('http')
async def db_middleware(request: Request, call_next):
    try:
        response: Response = await call_next(request)
        if 200 <= response.status_code < 400:
            Session.commit()
        else:
            Session.rollback()
    finally:
        Session.remove()

    return response
