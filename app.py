from typing import Any
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

class Metadata(BaseModel):
    table_name: str
    sql_create: str # CREATE TABLE statement
    columns: list[str] # list of column names that require insertion

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
        allow_origins=["http://localhost", "http://scraper"], # only allow from specific places, this service executes arbitrary SQL
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

@app.post("/insert")
def insert(metadata: Metadata, payload: list[Any]):
    try:
        cursor.execute(metadata.sql_create)
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
