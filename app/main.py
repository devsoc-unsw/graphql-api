import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from helpers.postgres import do_batch_insert
from helpers.auth import validate_api_key
from models import Metadata, BatchRequest


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://scraper"],
    # only allow from specific places, this service executes arbitrary SQL
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/batch_insert", dependencies=[Depends(validate_api_key)])
def batch_insert(requests: list[BatchRequest]):
    do_batch_insert(requests)
    return {}


@app.post("/insert", dependencies=[Depends(validate_api_key)])
def insert(metadata: Metadata, payload: list[Any]):
    do_batch_insert([BatchRequest(metadata=metadata, payload=payload)])
    return {}


if __name__ == '__main__':
    port = os.environ.get('HASURAGRES_PORT') or "8000"
    uvicorn.run(app, host="0.0.0.0", port=int(port))
