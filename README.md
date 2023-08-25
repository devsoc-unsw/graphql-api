# Hasuragres Service

## Querying Hasuragres



## Connecting Scrapers

Scrapers connecting to Hasuragres should accept two environment variables:
- `HASURAGRES_HOST`
- `HASURAGRES_PORT`

The scrape job should produce JSON output and send a HTTP POST request to `http://$HASURAGRES_HOST:$HASURAGRES_PORT/insert`.

### POST /insert

#### Parameters

| name                  | type         | description                                                                                                                                                                                                   |
|-----------------------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `metadata`            | object       | Instructions for creating/inserting into PostgreSQL tables.                                                                                                                                                   |
| `metadata.table_name` | str          | Name of table to create/insert into.<br/><br/>Must match name of table created in `metadata.sql_up` (case insensitive).                                                                                       |
| `metadata.columns`    | list[str]    | List of column names that require insertion.<br/><br/>Must match column names in table created in `metadata.sql_up`, as well as the keys of each object in `payload` (case sensitive).                        |
| `metadata.sql_up`     | str          | SQL script used to set UP (create) a table to store the scraped data, as well as any related data types.<br/><br/>If the script changes between `/insert` requests, the table is re-created.                  |
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
        "sql_up": "CREATE TABLE Students(
                       \"zId\"   INT PRIMARY KEY,
                       \"name\"  TEXT NOT NULL
                   );",
        "sql_down": "DROP TABLE Students CASCADE;"
    },
    "payload": [
        {"zId": 1, "name": "Student One"},
        {"zId": 2, "name": "Student Two"}
    ]
}

```
  
