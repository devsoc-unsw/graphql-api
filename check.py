

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