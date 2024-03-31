import os
import requests

from dotenv import load_dotenv

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


def send_hasura_api_query(query: dict):
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


def track_table(table_name: str):
    send_hasura_api_query({
        "type": "pg_track_table",
        "args": {
            "source": "default",
            "schema": "public",
            "name": table_name
        }
    })

    # Allow anonymous access
    send_hasura_api_query({
        "type": "pg_create_select_permission",
        "args": {
            "source": "default",
            "table": table_name,
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
        "args": infer_relationships(table_name)
    })


def untrack_table(table_name: str):
    send_hasura_api_query({
        "type": "pg_untrack_table",
        "args": {
            "source": "default",
            "cascade": True,
            "table": {
                "schema": "public",
                "name": table_name
            }
        }
    })
