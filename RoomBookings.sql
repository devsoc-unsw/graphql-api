
--  DROP TYPE BookingTypeEnum cascade;
 CREATE TYPE BookingTypeEnum AS ENUM ('STD', 'TLB', 'LEC', 'BLOCK', 'SOCIETY', 'SEM', 'WKS', 'OTH', 'LAB', 'EXM', 'LE0', 'MISC', 'INTERNAL', 'LA1', 'TUT', 'LE1', 'LE2');

--  DROP TABLE RoomBookings;
 CREATE TABLE RoomBookings (
 	Id		          SERIAL PRIMARY KEY ,
 	BookingType     BookingTypeEnum,
 	Name            TEXT NOT NULL,
 	RoomId          TEXT NOT NULL,
 	Start	          TIMESTAMP,
 	Finish	        TIMESTAMP
 );
