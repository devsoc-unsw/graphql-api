# CSESoc GraphQL API - powered by Hasura & Postgres

## Table of Contents

- [About Hasuragres](#about-hasuragres)
- [Querying Hasuragres](#querying-hasuragres)
- [Connecting Scrapers](#connecting-scrapers)
  - [POST `/insert` Route](#post-insert-route)
- [Testing Scrapers](#testing-scrapers)
  - [Troubleshooting](#troubleshooting)

## About Hasuragres

CSESoc provides a GraphQL API for all the data scraped and used for its various projects. In contrast to other unis, UNSW lacks public APIs for much of its data. We hope to fill that gap, so that other students may use this data to power their own personal projects.

This API provides data on:
- Buildings, rooms and room bookings (as seen in Freerooms)
- (COMING SOON) Course and class schedules (as seen in Notangles)
- (COMING SOON) Course information (as seen in Circles and Unilectives)

The API is powered by [Hasura](https://hasura.io/) - a powerful tool that hooks in to an existing database and automatically generates and exposes a rich GraphQL API for the data stored within. The underlying database we use is [Postgres](https://www.postgresql.org/), hence the name Hasuragres.

## Querying Hasuragres

To query the data available in Hasuragres, you can send a GraphQL request to `https://graphql.csesoc.app/v1/graphql`. You can explore the full GraphQL schema using our [interactive explorer](https://cloud.hasura.io/public/graphiql?endpoint=https%3A%2F%2Fgraphql.csesoc.app%2Fv1%2Fgraphql). For more information on the different kind of queries you can make with the Hasura GraphQL API, see [the docs](https://hasura.io/docs/latest/queries/postgres/index/#exploring-queries).

### Example

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

function fetchGraphQL(
  operationsDoc: string,
  operationName: string,
  variables: Record<string, any>
) {
  return fetch('https://graphql.csesoc.app/v1/graphql', {
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
        "id": "K-J17",
        "name": "Ainsworth Building",
        "rooms": [
          {
            "id": "K-J17-G03",
            "name": "Ainsworth G03",
            "capacity": 350
          }
        ]
      },
      {
        "id": "K-D23",
        "name": "Mathews Theatres",
        "rooms": [
          {
            "id": "K-D23-201",
            "name": "Mathews Theatre A",
            "capacity": 472
          },
          {
            "id": "K-D23-203",
            "name": "Mathews Theatre B",
            "capacity": 246
          },
          {
            "id": "K-D23-303",
            "name": "Mathews Theatre C",
            "capacity": 110
          },
          {
            "id": "K-D23-304",
            "name": "Mathews Theatre D",
            "capacity": 110
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

**Important Note**: If the scraper scrapes multiple entities, and one is the 'parent' of another, make sure to insert the parent first. For example, Freerooms scrapes buildings and rooms - each room belongs to a building, so buildings are inserted first. Otherwise, foreign key constraints will not be satisfied.


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
## Testing Scrapers

The recommended way to test whether the scraper is connected correctly is to run Hasuragres locally, attempt to connect to the local instance of Hasuragres and, if that works without errors, manually inspect the Hasura console to check the data appears correct.

To run Hasuragres locally, clone this repo, then in the root directly of the repo, run `docker compose up -d` (you will need Docker Desktop). This will use port 8000 for connecting scrapers, and port 8080 for Hasura. These ports can be configured in the `.env` file.

As described above, your scraper should use the environment variables `HASURAGRES_HOST` and `HASURAGRES_PORT`. Set these to `localhost` and `8000` respectively and run your scraper.

Once that completes, go to `http://localhost:8080/console` and enter the admin secret (`hasurasecret` by default, configured in the `.env` file). If everything is correct, you should see all your tables in the "sidebar" of the API tab. You can also go to the Data tab to inspect the data directly.

### Troubleshooting

Most commonly, missing tables or data will come from a bad request to `/insert` causing the operation to fail. You can take a look at the logs for the `hasuragres` service in Docker Desktop - these should output why the request failed.

Common errors include:
- **"Error while creating PostgreSQL table"**, which might occur if:
  - `sql_up` is incorrectly formatted
  - if updating the table structure, the old `sql_down` did not correctly drop all structures
- **"Error while inserting into PostgreSQL table"**, which might occur if:
  - the data is malformed (i.e. columns missing or named inconsistently, constraints not satisfied)
  - table name does not match the name of the table created in `sql_up`
