import os
from contextlib import asynccontextmanager
from typing import Any, Annotated

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extensions import connection

from helpers.postgres import do_batch_insert, get_db_conn, shutdown_db
from helpers.auth import validate_api_key
from models import Metadata, BatchRequest

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    shutdown_db()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://scraper"],
    # only allow from specific places, this service executes arbitrary SQL
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/batch_insert", dependencies=[Depends(validate_api_key)])
def batch_insert(requests: list[BatchRequest], conn: Annotated[connection, Depends(get_db_conn)]):
    do_batch_insert(conn, requests)
    return {}


@app.post("/insert", dependencies=[Depends(validate_api_key)])
def insert(metadata: Metadata, payload: list[Any], conn: Annotated[connection, Depends(get_db_conn)]):
    do_batch_insert(conn, [BatchRequest(metadata=metadata, payload=payload)])
    return {}


if __name__ == '__main__':
    port = os.environ.get('HASURAGRES_PORT') or "8000"
    uvicorn.run(app, host="0.0.0.0", port=int(port))
