# Connecting Scrapers

**Note: The following section contains instructions for DevSoc internal teams. For general usage, see [here](README.md).**

Hasuragres has been designed with a "plug-and-play" functionality in mind for connecting scrapers. The logic of the scraper should not need to change, as long as it can produce JSON output in a structured schema and send this over HTTP.

Scrapers connecting to Hasuragres should accept two environment variables:
- `HASURAGRES_URL`
- `HASURAGRES_API_KEY`

The scrape job should produce JSON output and send a HTTP POST request to `$HASURAGRES_URL/insert` with the `X-API-Key` header set to `$HASURAGRES_API_KEY` - see below for more information

**Important Note**: If the scraper scrapes multiple entities, and one references another, make sure to insert the referenced table first. For example, Freerooms scrapes buildings and rooms - each room belongs to a building, so buildings are inserted first. Otherwise, foreign key constraints will not be satisfied.

## POST `/insert` Route

### Description

Inserts data into the PostgreSQL table specified by `table_name`. If such a table does not yet exist, it is created as specified in `sql_up`.

Insertion into Hasuragres uses 'upsertion' logic. This means that when inserting rows, if there is already an existing row with the same primary key, we update that row rather than raising an error. If `write_mode` is set to `"overwrite"` (default), any rows that were not inserted or upserted in the current insert operation are also deleted.

Hasuragres keeps track of the SQL scripts used to create each table. If there is an inconsistency between the stored `sql_up` script and the one provided in the request, then the table is re-created using the new `sql_up`. The stored `sql_down` is used to drop the old table - it's important that `sql_down` is correct, otherwise updates to the table structure may fail.

When a table is created, it is automatically tracked in Hasura and added to the GraphQL Schema. Three query fields are added in the GraphQL Schema (note that `table_name` will be in lowercase):
- `<table_name>` - contains all fields/relationships of the table
- `<table_name>_by_pk` - as above, specifically optimised for querying a single row using 
- `<table_name>_aggregate` - aggregation operations on the table using the primary key column(s)

Furthermore, any foreign key relationships are inferred, and fields containing nested objects are added to each relevant queryable data type. More information can be found [here](https://hasura.io/docs/latest/getting-started/how-it-works/index/).

### Parameters

| name                  | type         | required | description                                                                                                                                                                                                     |
|-----------------------|--------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `metadata`            | object       | Yes      | Instructions for creating/inserting into PostgreSQL tables.                                                                                                                                                     |
| `metadata.table_name` | str          | Yes      | Name of table to create/insert into.<br/><br/>Must match name of table created in `metadata.sql_up` (case insensitive).                                                                                         |
| `metadata.columns`    | list[str]    | Yes      | List of column names that require insertion.<br/><br/>Must match column names in table created in `metadata.sql_up`, as well as the keys of each object in `payload` (case sensitive).                          |
| `metadata.write_mode` | str          | No       | One of `"overwrite"` or `"append"`.<br/><br/>Defaults to `"overwrite"`.                                                                                                                                         |
| `metadata.sql_before` | str          | No       | SQL command to run *before* the insertion.                                                                                                                                                                      |
| `metadata.sql_after`  | str          | No       | SQL command to run *after* the insertion.                                                                                                                                                                       |
| `metadata.sql_up`     | str          | Yes      | SQL commands used to set UP (create) a table to store the scraped data, as well as any related objects (types, indexes, triggers).                                                                              |
| `metadata.sql_down`   | str          | Yes      | SQL commands to tear DOWN (drop) all objects created by `metadata.sql_up`.<br/><br/>Should use the CASCADE option when dropping, otherwise the script may fail unexpectedly when other tables rely on this one. |
| `metadata.dryrun`     | bool         | No       | If true, attempts to run the insert but does not commit changes to the database.<br/><br/>Useful for testing.                                                                                                   |
| `payload`             | list[object] | Yes      | List of objects to insert into the database.<br/><br/>Ideally, this is simply the JSON output of the scraper.                                                                                                   |

### Authorisation

To POST to Hasuragres, you will need to provide an API key. To receive one, please ask the Platform team to:
- Generate a new key
- Inject it as an environment variable (`HASURAGRES_API_KEY`) in to the scraper
- Add it to the list of API keys (`API_KEYS`) injected in to Hasuragres
- (if needed for CI) Add the key to the scraper repository secrets

In your request, send the API key as an `X-API-Key` header.

### Example Request

```http request
POST /insert HTTP/1.1
Content-Type: application/json
X-API-Key: my_key

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

## Multiple Scrapers for One Table

If you want to connect multiple scrapers to the same table, for example if you have multiple data sources, then Hasuragres is able to support this. Follow the guidelines below to set this up.

Both scrapers should maintain an up-to-date copy of the `sql_up` and `sql_down` commands sent to Hasuragres. Furthermore, if you need to update these commands, please be sure to update all scrapers around the same time without much delay between each. If at any point the scrapers have different versions of the SQL, then any inserts will simply drop the table and all data from the other scraper(s). To ensure this, it may be useful to house all the scrapers in a monorepo.

It is also important that you make use of the `sql_before` and `write_mode` fields of the insert metadata:
- By default, inserts are set to remove any rows not inserted/updated by the current scraper insert, which would only allow data from one scraper at any one time. For multiple scrapers, they should each be in `"append"` mode so that scrapers can add on to the data from other scrapers.
- `sql_before` should contain commands(s) to remove only those rows that were previously inserted by the scraper - it may be useful to add some field to the schema that identifies the source of each row if there is no easy way to distinguish between the data sources.

## Testing Scrapers

### Testing Locally

The recommended way to test whether the scraper is connected correctly is to run Hasuragres locally, attempt to connect to the local instance of Hasuragres and, if that works without errors, manually inspect the Hasura console to check the data appears correct.

To run Hasuragres locally, clone this repo, then in the root directly of the repo, run `docker compose up -d` (you will need Docker Desktop). This will use port 8000 for connecting scrapers, and port 8080 for Hasura. These ports can be configured in the `.env` file.

As described above, your scraper should use the environment variables `HASURAGRES_URL` and `HASURAGRES_API_KEY`. Set these to `http://localhost:8000` and `my_key` respectively (or whatever you have configured them to in `.env`) and run your scraper.

Once that completes, go to `http://localhost:8080/console` and enter the admin secret (`hasurasecret` by default, configured in the `.env` file). If everything is correct, you should see all your tables in the "sidebar" of the API tab, and you can try out some queries. You can also go to the Data tab to inspect the data directly.

### Dryrun on Deployed Instance

You can also test by running a dryrun request to the deployed instance of Hasuragres at `https://graphql.csesoc.app`. This can be useful for CI or simply as a sanity check.

To do so, set `HASURAGRES_URL` to `https://graphql.csesoc.app`, set `HASURAGRES_API_KEY` to the key issued for your scraper, and set the `metadata.dryrun` field in the body of the request to `true`.

### Troubleshooting

Most commonly, missing tables or data will come from a bad request to `/insert` causing the operation to fail. You can take a look at the logs for the `hasuragres` service in Docker Desktop - these should output why the request failed.

Common errors include:
- **"Error while creating PostgreSQL table"**, which might occur if:
  - `sql_up` is incorrectly formatted
  - if updating the table structure, the old `sql_down` did not correctly drop all structures
- **"Error while inserting into PostgreSQL table"**, which might occur if:
  - the data is malformed (i.e. columns missing or named inconsistently, constraints not satisfied)
  - table name does not match the name of the table created in `sql_up`