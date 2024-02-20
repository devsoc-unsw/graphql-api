import os
from typing import Any, Literal, Optional

import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import Error
from psycopg2.extensions import connection, cursor
from pydantic import BaseModel, Field

from helpers.hasura import track_table


class Metadata(BaseModel):
    table_name: str
    sql_before: Optional[str] = Field(None, description='command to execute before running the insert')
    sql_after: Optional[str] = Field(None, description='command to execute after running the insert')
    sql_up: str         # SQL to set UP table and related data types/indexes
    sql_down: str       # SQL to tear DOWN a table (should be the opp. of up)
    columns: list[str]  # list of column names that require insertion
    write_mode: Literal['append', 'overwrite'] = Field('overwrite', description='mode in which to write to the database')


conn: connection = None
cur: cursor = None

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
    cur.execute(open("app/init.sql", "r").read())

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


def get_primary_key_columns(table_name: str) -> list[str]:
    cmd = f"""
        SELECT c.column_name
        FROM information_schema.columns c
            JOIN information_schema.key_column_usage kcu
                ON c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
            JOIN information_schema.table_constraints tc
                ON kcu.table_name = tc.table_name
                AND kcu.constraint_name = tc.constraint_name
        WHERE c.table_name = '{table_name}'
            AND tc.constraint_type = 'PRIMARY KEY';
    """
    cur.execute(cmd)

    return [row[0] for row in cur.fetchall()]


def execute_upsert(metadata: Metadata, payload: list[Any]):
    columns = [f'"{col}"' for col in metadata.columns]
    key_columns = [f'"{col}"' for col in get_primary_key_columns(metadata.table_name)]
    non_key_columns = [col for col in columns if col not in key_columns]

    cmd = f"""
        INSERT INTO {metadata.table_name}({", ".join(columns)})
        VALUES ({", ".join(["%s"] * len(columns))})
        ON CONFLICT ({", ".join(key_columns)})
        DO UPDATE SET {", ".join(f"{col} = EXCLUDED.{col}" for col in non_key_columns)};
    """
    values = [tuple(row[col] for col in metadata.columns) for row in payload]

    cur.executemany(cmd, values)


def execute_delete(metadata: Metadata, payload: list[Any]):
    key_columns = get_primary_key_columns(metadata.table_name)
    quoted_key_columns = [f'"{col}"' for col in key_columns]

    cmd = f"""
        DELETE FROM {metadata.table_name}
        WHERE ({", ".join(quoted_key_columns)}) NOT IN %s;
    """
    values = tuple(tuple(row[col] for col in key_columns) for row in payload)

    cur.execute(cmd, (values,))


@app.post("/insert")
def insert(metadata: Metadata, payload: list[Any]):
    try:
        created = create_table(metadata)
    except (Exception, Error) as error:
        err_msg = "Error while creating PostgreSQL table: " + str(error)
        print(err_msg)
        conn.rollback()
        raise HTTPException(status_code=400, detail=err_msg)

    try:
        if metadata.sql_before:
            cur.execute(metadata.sql_before)

        execute_upsert(metadata, payload)
        if metadata.write_mode == 'overwrite':
            # Delete rows not in payload
            execute_delete(metadata, payload)

        if metadata.sql_after:
            cur.execute(metadata.sql_after)
    except (Exception, Error) as error:
        err_msg = "Error while inserting into PostgreSQL table: " + str(error)
        print(err_msg)
        conn.rollback()
        raise HTTPException(status_code=400, detail=err_msg)

    conn.commit()

    # Run Hasura actions - must be done after transaction committed otherwise Hasura won't see the table
    if created:
        track_table(metadata.table_name.lower())

    return {}


if __name__ == '__main__':
    port = os.environ.get('HASURAGRES_PORT') or "8000"
    uvicorn.run(app, host="0.0.0.0", port=int(port))
