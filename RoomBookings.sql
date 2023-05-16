
--  DROP TYPE BookingTypeEnum cascade;
 CREATE TYPE BookingTypeEnum AS ENUM ('CLASS', 'BLOCK', 'SOCIETY', 'MISC', 'INTERNAL');

--  DROP TABLE RoomBookings;
 CREATE TABLE RoomBookings (
    'id'            SERIAL PRIMARY KEY ,
    'bookingType'   BookingTypeEnum,
    'name'          TEXT NOT NULL,
    'roomId'        TEXT NOT NULL,
    'start'         TIMESTAMP,
    'end'           TIMESTAMP
 );
