# CSESoc's GraphQL API - powered by Hasura & Postgres

## Table of Contents

- [About Hasuragres](#about-hasuragres)
- [Querying Hasuragres](#querying-hasuragres)
- [Connecting Scrapers](#connecting-scrapers)

## About Hasuragres

API for all of CSESoc's scraped data.

## Querying Hasuragres

To query the data available in Hasuragres, you can send a GraphQL request to `https://graphql.csesoc.app/v1/graphql`. You can explore the full GraphQL schema using our [interactive explorer](https://cloud.hasura.io/public/graphiql?endpoint=https%3A%2F%2Fgraphql.csesoc.app%2Fv1%2Fgraphql). For more information on the different kind of queries you can make with the Hasura GraphQL API, see [the docs](https://hasura.io/docs/latest/queries/postgres/index/#exploring-queries).

Here is an example query to fetch all buildings at UNSW with a room that has a capacity greater than 100, along with all of those rooms sorted in descending order of capacity:
```gql
query MyQuery {
  buildings(where: {rooms: {capacity: {_gt: 100}}}) {
    id
    name
    rooms(where: {capacity: {_gt: 100}}, order_by: {capacity: desc}) {
      id
      name
      capacity
    }
  }
}
```

Here's an example of how we might send this query using TypeScript (using the interactive explorer linked above!):
```ts
/*
This is an example snippet - you should consider tailoring it
to your service.

Note: we only handle the first operation here
*/

function fetchGraphQL(
  operationsDoc: string,
  operationName: string,
  variables: Record<string, any>
) {
  return fetch('undefined', {
    method: 'POST',
    body: JSON.stringify({
      query: operationsDoc,
      variables,
      operationName,
    }),
  }).then(result => result.json());
}

const operation = `
  {
    buildings(where: {rooms: {capacity: {_gt: 100}}}) {
      id
      name
      rooms(where: {capacity: {_gt: 100}}, order_by: {capacity: desc}) {
        id
        name
        capacity
      }
    }
  }
`;

function fetchquery() {
  return fetchGraphQL(operations, query, {})
}

fetchquery()
  .then(({ data, errors }) => {
    if (errors) {
      console.error(errors);
    }
    console.log(data);
  })
  .catch(error => {
    console.error(error);
  });
```

Here is a snippet of what this query might return:
```json
{
  "data": {
    "buildings": [
      {
        "id": "K-G27",
        "name": "AGSM",
        "rooms": [
          {
            "id": "K-G27-G07",
            "name": "John B Reid Theatre",
            "capacity": 131
          }
        ]
      },
      {
        "id": "K-J17",
        "name": "Ainsworth Building",
        "rooms": [
          {
            "id": "K-J17-G03",
            "name": "Ainsworth G03",
            "capacity": 350
          }
        ]
      }
    ]
  }
}
```



## Connecting Scrapers

Scrapers connecting to Hasuragres should accept two environment variables:
- `HASURAGRES_HOST`
- `HASURAGRES_PORT`

The scrape job should produce JSON output and send a HTTP POST request to `http://$HASURAGRES_HOST:$HASURAGRES_PORT/insert`.


### POST `/insert` Route

#### Description

Inserts data into the PostgreSQL table specified by `table_name`. If such a table does not yet exist, it is created as specified in `sql_up`.

Hasuragres keeps track of the SQL scripts used to create each table. If there is an inconsistency between the stored `sql_up` script and the one provided in the request, then the table is re-created using the new `sql_up`. The stored `sql_down` is used to drop the old table - it's important that `sql_down` is correct, otherwise updates to the table structure may fail.

When a table is created, it is automatically tracked in Hasura and added to the GraphQL Schema. Corresponding query fields are created called `<table_name>` and `<table_name>_by_pk` (note that `table_name` will be in lowercase), with fields for each column of the table. Furthermore, any foreign key relationships are inferred, and fields containing nested objects are added to each relevant queryable data type. More information can be found [here](https://hasura.io/docs/latest/getting-started/how-it-works/index/).

#### Parameters

| name                  | type         | description                                                                                                                                                                                                   |
|-----------------------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `metadata`            | object       | Instructions for creating/inserting into PostgreSQL tables.                                                                                                                                                   |
| `metadata.table_name` | str          | Name of table to create/insert into.<br/><br/>Must match name of table created in `metadata.sql_up` (case insensitive).                                                                                       |
| `metadata.columns`    | list[str]    | List of column names that require insertion.<br/><br/>Must match column names in table created in `metadata.sql_up`, as well as the keys of each object in `payload` (case sensitive).                        |
| `metadata.sql_up`     | str          | SQL script used to set UP (create) a table to store the scraped data, as well as any related data types.                                                                                                      |
| `metadata.sql_down`   | str          | SQL script to tear DOWN (drop) all objects created by `metadata.sql_up`.<br/><br/>Should use the CASCADE option when dropping, otherwise the script may fail unexpectedly when other tables rely on this one. |
| `payload`             | list[object] | List of objects to insert into the database.<br/><br/>Ideally, this is simply the JSON output of the scraper.                                                                                                 |

#### Example Request

```http request
POST /insert HTTP/1.1
Content-Type: application/json

{
    "metadata": {
        "table_name": "students",
        "columns": ["zId", "name"],
        "sql_up": "CREATE TABLE Students(\"zId\" INT PRIMARY KEY, \"name\" TEXT);",
        "sql_down": "DROP TABLE Students CASCADE;"
    },
    "payload": [
        {"zId": 1, "name": "Student One"},
        {"zId": 2, "name": "Student Two"}
    ]
}

```
### Testing Scrapers

Clone this repo, `docker compose up -d`, run the scraper with host `localhost` and port `8000`. Go to `http://localhost:8080/console` and enter the admin secret. See if everything is there.
