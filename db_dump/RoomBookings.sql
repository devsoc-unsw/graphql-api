
--  DROP TABLE Buildings CASCADE;
 CREATE TABLE IF NOT EXISTS Buildings (
	"id"	TEXT PRIMARY KEY,
	"name"	TEXT NOT NULL,
	"lat"	DOUBLE PRECISION NOT NULL,
	"long"	DOUBLE PRECISION NOT NULL
 );

--  DROP TABLE RoomBookings CASCADE;
--  ALTER TABLE Rooms ADD FOREIGN KEY ("buildingId") REFERENCES Buildings("id") ON DELETE CASCADE;
 CREATE TABLE IF NOT EXISTS Rooms (
	"id"			TEXT PRIMARY KEY,
	"name"			TEXT NOT NULL,
	"abbr"			TEXT NOT NULL,	
	"usage"			TEXT NOT NULL,
	"capacity"		INTEGER NOT NULL,
	"school"		TEXT NOT NULL,
	"buildingId"	TEXT NOT NULL,
	FOREIGN KEY ("buildingId") REFERENCES Buildings("id") ON DELETE CASCADE
 );

--  DROP TYPE BookingTypeEnum CASCADE;
 CREATE TYPE BookingTypeEnum AS ENUM ('CLASS', 'BLOCK', 'SOCIETY', 'MISC', 'INTERNAL');

--  DROP TABLE Bookings;
 CREATE TABLE IF NOT EXISTS Bookings (
    "id"            SERIAL PRIMARY KEY,
    "bookingType"   BookingTypeEnum,
    "name"          TEXT NOT NULL,
    "roomId"        TEXT NOT NULL,
    "start"         TIMESTAMPTZ NOT NULL,
    "end"           TIMESTAMPTZ NOT NULL,
     FOREIGN KEY ("roomId") REFERENCES Rooms("id") ON DELETE CASCADE
 );

CREATE INDEX bookings_start_end ON Bookings ("start", "end")
