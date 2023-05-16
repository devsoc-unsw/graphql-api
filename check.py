

import json
import psycopg2
from psycopg2 import Error


def get_query_values():
    f = open('bookings.json')
    data = json.load(f)
    values = []
    for booking in data:
        tp, name, room_id, start, end = booking.values()
        values.append((tp, name, room_id, start, end))
    return values
try:
    connection = psycopg2.connect(user="postgres",
                                  password="postgrespassword",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="postgres")

    cursor = connection.cursor()
    cmd = "INSERT INTO RoomBookings(BOOKINGTYPE, NAME, ROOMID, START, FINISH) VALUES (%s, %s, %s, %s, %s)"
    print(get_query_values())
    cursor.executemany(cmd, get_query_values())
    connection.commit()
    # cursor.execute("SELECT * FROM ROOMBOOKINGS;")
    # row = cursor.fetchone()
    # while row is not None:
    #     print(row)
    #     row = cursor.fetchone()
except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    if (connection):
        cursor.close()
        connection.close()
        print("PostgreSQL connection is closed")



