import os
from typing import Any, Literal, Optional

import psycopg2
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import Error
from psycopg2.extensions import connection, cursor
from pydantic import BaseModel, Field

# Ensure HASURA_GRAPHQL_ env vars are set
load_dotenv()
HGQLA_SECRET = os.environ.get("HASURA_GRAPHQL_ADMIN_SECRET")
if not HGQLA_SECRET:
    print("HASURA_GRAPHQL_ADMIN_SECRET not set")
    exit(1)

HGQL_HOST = os.environ.get('HASURA_GRAPHQL_HOST')
if not HGQL_HOST:
    print("HASURA_GRAPHQL_HOST not set")
    exit(1)

HGQL_PORT = os.environ.get('HASURA_GRAPHQL_PORT')
if not HGQL_PORT:
    print("HASURA_GRAPHQL_PORT not set")
    exit(1)


class Metadata(BaseModel):
    table_name: str
    sql_execute: Optional[str] = Field(None, description='command to execute before running anything else')
    sql_up: str         # SQL to set UP table and related data types/indexes
    sql_down: str       # SQL to tear DOWN a table (should be the opp. of up)
    columns: list[str]  # list of column names that require insertion
    write_mode: Optional[Literal['append'] | Literal['truncate']] = Field('truncate', description='mode in which to write to the database')


conn = None
cur = None

try:
    conn = psycopg2.connect(user=os.environ.get('POSTGRES_USER'),
                                  password=os.environ.get('POSTGRES_PASSWORD'),
                                  host=os.environ.get('POSTGRES_HOST'),
                                  port=os.environ.get('POSTGRES_PORT'),
                                  database=os.environ.get('POSTGRES_DB'))
    cur = conn.cursor()

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://scraper"],
        # only allow from specific places, this service executes arbitrary SQL
        allow_methods=["*"],
        allow_headers=["*"],
    )
except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
    if conn:
        conn.close()
        if cur:
            cur.close()
        print("PostgreSQL connection is closed")
    exit(1)


def create_table(metadata: Metadata) -> bool:
    """
    Create table as specified in metadata.

    If table already exists, and sql_up is up-to-date, do nothing. If
    sql_up has been changed, run the stored sql_drop, and create table
    as specified in new sql_up.

    Returns whether the table was created or not.
    """

    # Initialise Tables table if not already
    cmd = """
    CREATE TABLE IF NOT EXISTS Tables (
        table_name  TEXT PRIMARY KEY,
        up      	TEXT NOT NULL,
        down       	TEXT NOT NULL
    )
    """
    cur.execute(cmd)

    cmd = r"SELECT up, down FROM Tables WHERE table_name = %s"
    metadata.table_name = metadata.table_name.lower()
    cur.execute(cmd, (metadata.table_name,))
    table_sql = cur.fetchone()
    if not table_sql:
        # Execute create table
        cur.execute(metadata.sql_up)

        # Store metadata
        cmd = r"INSERT INTO Tables(table_name, up, down) VALUES (%s, %s, %s)"
        cur.execute(cmd, (metadata.table_name, metadata.sql_up, metadata.sql_down))

        return True
    elif table_sql[0] != metadata.sql_up:
        # Re-create
        cur.execute(table_sql[1])  # old sql_down
        cur.execute(metadata.sql_up)

        # Store new metadata
        cmd = r"UPDATE Tables SET up = %s, down = %s WHERE table_name = %s"
        cur.execute(cmd, (metadata.sql_up, metadata.sql_down, metadata.table_name))

        return True

    return False


def send_hasura_api_query(query: object):
    return requests.post(
        f"http://{HGQL_HOST}:{HGQL_PORT}/v1/metadata",
        headers={
            "X-Hasura-Admin-Secret": HGQLA_SECRET
        },
        json=query
    )


# The below functions are used to adhere to Hasura's relationship nomenclature
# https://hasura.io/docs/latest/schema/postgres/using-existing-database/
# Possibly use the `inflect` module if they aren't sufficient
def plural(s: str) -> str:
    return s if s.endswith("s") else s + "s"


def singular(s: str) -> str:
    return s if not s.endswith("s") else s[:-1]


def infer_relationships(table_name: str) -> list[object]:
    """
    Use pg_suggest_relationships to infer any relations from foreign keys
    in the given table. Returns an array containing queries to track each
    relationship.

    See https://hasura.io/docs/latest/api-reference/metadata-api/relationship/
    """
    res = send_hasura_api_query({
        "type": "pg_suggest_relationships",
        "version": 1,
        "args": {
            "omit_tracked": True,
            "tables": [table_name]
        }
    })

    queries = []
    for rel in res.json()["relationships"]:
        if rel["type"] == "object":
            queries.append({
                "type": "pg_create_object_relationship",
                "args": {
                    "source": "default",
                    "table": rel["from"]["table"]["name"],
                    "name": singular(rel["to"]["table"]["name"]),
                    "using": {
                        "foreign_key_constraint_on": rel["from"]["columns"]
                    }
                }
            })
        elif rel["type"] == "array":
            queries.append({
                "type": "pg_create_array_relationship",
                "args": {
                    "source": "default",
                    "table": rel["from"]["table"]["name"],
                    "name": plural(rel["to"]["table"]["name"]),
                    "using": {
                        "foreign_key_constraint_on": {
                            "table": rel["to"]["table"]["name"],
                            "columns": rel["to"]["columns"]
                        }
                    }
                }
            })

    return queries


@app.post("/insert")
def insert(metadata: Metadata, payload: list[Any]):
    try:
        created = create_table(metadata)
    except (Exception, Error) as error:
        print("Error while creating PostgreSQL table:", error)
        conn.rollback()
        return {"status": "error", "error": str(error)}

    try:
        # execute whatever SQL is required
        if metadata.sql_execute:
            cur.execute(metadata.sql_execute)
        if metadata.write_mode == 'truncate':
            # Remove old data
            cmd = f'TRUNCATE {metadata.table_name} CASCADE'
            cur.execute(cmd)

        # Insert new data
        values = [tuple(row[col] for col in metadata.columns) for row in payload]
        metadata.columns = [f'"{col}"' for col in metadata.columns]
        cmd = f'INSERT INTO {metadata.table_name}({", ".join(metadata.columns)}) VALUES ({", ".join(["%s"] * len(metadata.columns))})'
        cur.executemany(cmd, values)
    except (Exception, Error) as error:
        print("Error while inserting into PostgreSQL table:", error)
        conn.rollback()
        return {"status": "error", "error": str(error)}

    conn.commit()

    # Run Hasura actions - must be done after transaction committed
    if created:
        # Track table
        send_hasura_api_query({
            "type": "pg_track_table",
            "args": {
                "source": "default",
                "schema": "public",
                "name": metadata.table_name.lower()
            }
        })

        # Allow anonymous access
        send_hasura_api_query({
            "type": "pg_create_select_permission",
            "args": {
                "source": "default",
                "table": metadata.table_name.lower(),
                "role": "anonymous",
                "permission": {
                    "columns": "*",
                    "filter": {},
                    "allow_aggregations": True
                }
            }
        })

        # Track relationships
        send_hasura_api_query({
            "type": "bulk",
            "args": infer_relationships(metadata.table_name.lower())
        })

    return {"status": "success"}


if __name__ == '__main__':
    port = os.environ.get('HASURAGRES_PORT') or "8000"
    uvicorn.run(app, host="0.0.0.0", port=int(port))
