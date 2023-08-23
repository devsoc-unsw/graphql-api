from typing import Any
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests


class Metadata(BaseModel):
    table_name: str
    sql_up: str         # SQL to set UP table and related data types/indexes
    sql_down: str       # SQL to tear DOWN a table (should be the opp. of up)
    columns: list[str]  # list of column names that require insertion


connection = None
cursor = None
load_dotenv()
try:
    connection = psycopg2.connect(user=os.environ.get('POSTGRES_USER'),
                                  password=os.environ.get('POSTGRES_PASSWORD'),
                                  host="postgres",
                                  port=os.environ.get('POSTGRES_PORT'),
                                  database=os.environ.get('POSTGRES_DB'))
    cursor = connection.cursor()
    app = FastAPI(port=os.environ.get('PORT'))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost", "http://scraper"],
        # only allow from specific places, this service executes arbitrary SQL
        allow_methods=["*"],
        allow_headers=["*"],
    )
except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
    if connection:
        connection.close()
        if cursor:
            cursor.close()
        print("PostgreSQL connection is closed")
    exit(1)


def create_table(metadata: Metadata):
    """
    Create table as specified in metadata.

    If table already exists, and sql_up is up-to-date, do nothing. If
    sql_up has been changed, run the stored sql_drop, and create table
    as specified in new sql_up.

    Also tracks the table on Hasura.
    """
    cmd = f"SELECT up, down FROM Tables WHERE table_name = %s LIMIT 1"
    cursor.execute(cmd, (metadata.table_name,))
    table_sql = cursor.fetchone()
    if not table_sql:
        # Does not exist
        cursor.execute(metadata.sql_up)
        requests.post(
            "http://localhost:8080/v1/metadata",
            headers={
                "X-Hasura-Admin-Secret": os.environ.get("HASURA_GRAPHQL_ADMIN_SECRET")
            },
            json={
                "type": "pg_track_table",
                "args": {
                    "source": "postgres",
                    "schema": "public",
                    "name": metadata.table_name
                }
            }
        )
    elif table_sql['up'] != metadata.sql_up:
        # Re-create table
        cursor.execute(table_sql['down'])
        cursor.execute(metadata.sql_up)

        # Store new metadata
        cmd = f"UPDATE Tables SET up = %s, down = %s WHERE table_name = %s LIMIT 1"
        cursor.execute(cmd, (metadata.sql_up, metadata.sql_down, metadata.table_name))


@app.post("/insert")
def insert(metadata: Metadata, payload: list[Any]):
    try:
        create_table(metadata)
    except (Exception, Error) as error:
        print("Error while creating PostgreSQL table", error)
        connection.rollback()
        return {"status": "error", "error": str(error)}

    metadata.columns = [col.lower() for col in metadata.columns]
    values = [tuple(row[col] for col in metadata.columns) for row in payload]
    cmd = f'INSERT INTO {metadata.table_name}({", ".join(metadata.columns)}) VALUES ({", ".join(["%s"] * len(metadata.columns))}) ON CONFLICT (id) DO UPDATE SET {", ".join([f"{col}=EXCLUDED.{col}" for col in metadata.columns])}'
    try:
        cursor.executemany(cmd, values)
        connection.commit()
    except (Exception, Error) as error:
        print("Error while inserting into PostgreSQL table", error)
        connection.rollback()
        return {"status": "error", "error": str(error)}

    return {"status": "success"}


if __name__ == '__main__':
    port = os.environ.get('PORT') or "8000"
    uvicorn.run(app, host="0.0.0.0", port=int(port))
