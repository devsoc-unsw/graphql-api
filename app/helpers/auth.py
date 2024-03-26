import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()
API_KEYS = list(filter(None, os.environ.get("API_KEYS", "").split(";")))


def validate_api_key(x_api_key: Annotated[str, Header()] = ""):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="X-API-Key invalid or missing")
