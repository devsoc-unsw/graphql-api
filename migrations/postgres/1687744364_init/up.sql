-- SQL to set up table to track other tables

CREATE TABLE IF NOT EXISTS Tables (
    table_name  TEXT PRIMARY KEY,
	up      	TEXT NOT NULL,
	down       	TEXT NOT NULL
)
