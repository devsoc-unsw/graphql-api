
# DROP TYPE BookingTypeEnum cascade;
# CREATE TYPE BookingTypeEnum AS ENUM ('STD', 'TLB', 'LEC', 'BLOCK', 'SOCIETY', 'SEM', 'WKS', 'OTH', 'LAB', 'EXM', 'LE0', 'MISC', 'INTERNAL', 'LA1', 'TUT', 'LE1', 'LE2');

# DROP TABLE RoomBookings;
# CREATE TABLE RoomBookings (
# 	Id		        SERIAL PRIMARY KEY ,
# 	BookingType     BookingTypeEnum,
# 	Name            TEXT NOT NULL,
# 	RoomId          TEXT NOT NULL,
# 	Start	        TIMESTAMP,
# 	Finish	        TIMESTAMP
# );


import json


f = open('bookings.json')
data = json.load(f)
names = set()
sql_query = "INSERT INTO RoomBookings(BOOKINGTYPE, NAME, ROOMID, START, FINISH) VALUES"
n = len(data);
for id, booking in enumerate(data):
    tp, name, room_id, start, end = booking.values()
    sql_query += f"(\'{tp}\' , \'{name}\' , \'{room_id}\', \'{start}\', \'{end}\')"
    if id == n - 1:
        sql_query += ';'
    else:
        sql_query += ', '
print(sql_query)


