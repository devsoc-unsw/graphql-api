CREATE TABLE Buildings (
    "id"        TEXT PRIMARY KEY,
    "name"      TEXT NOT NULL,
    "lat"       DOUBLE PRECISION NOT NULL,
    "long"      DOUBLE PRECISION NOT NULL,
    "aliases"   TEXT[] NOT NULL
);


CREATE TABLE Rooms (
    "id"            TEXT PRIMARY KEY,
    "name"          TEXT NOT NULL,
    "abbr"          TEXT NOT NULL,	
    "usage"         TEXT NOT NULL,
    "capacity"      INTEGER NOT NULL,
    "school"        TEXT NOT NULL,
    "buildingId"    TEXT NOT NULL,
    FOREIGN KEY ("buildingId") REFERENCES Buildings("id") ON DELETE CASCADE
);

CREATE TYPE BookingTypeEnum AS ENUM ('CLASS', 'BLOCK', 'SOCIETY', 'MISC', 'INTERNAL');

CREATE TABLE Bookings (
    "id"            SERIAL PRIMARY KEY,
    "bookingType"   BookingTypeEnum,
    "name"          TEXT NOT NULL,
    "roomId"        TEXT NOT NULL,
    "start"         TIMESTAMPTZ NOT NULL,
    "end"           TIMESTAMPTZ NOT NULL,
    FOREIGN KEY ("roomId") REFERENCES Rooms("id") ON DELETE CASCADE
);

CREATE INDEX bookings_start_end ON Bookings ("start", "end")
