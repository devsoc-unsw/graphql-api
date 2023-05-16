import json
import psycopg2
from psycopg2 import Error

def insert_buildings(cursor):
    with open('buildings.json') as f:
        data = json.load(f)
    values = [(bldg['id'], bldg['name'], bldg['lat'], bldg['long']) for bldg in data]

    cmd = 'INSERT INTO Buildings("id", "name", "lat", "long") VALUES (%s, %s, %s, %s)'
    cursor.executemany(cmd, values)


def insert_rooms(cursor):
    with open('rooms.json') as f:
        data = json.load(f)
    values = [(
        room['id'],
        room['name'],
        room['abbr'],
        room['usage'],
        room['capacity'],
        room['school'],
        '-'.join(room['id'].split('-')[:1])
    ) for room in data]

    cmd = 'INSERT INTO Rooms("id", "name", "abbr", "usage", "capacity", "school", "buildingId") VALUES (%s, %s, %s, %s, %s, %s, %s)'
    cursor.executemany(cmd, values)


def insert_bookings(cursor):
    with open('bookings.json') as f:
        data = json.load(f)
    values = [(
        booking['bookingType'],
        booking['name'],
        booking['roomId'],
        booking['start'],
        booking['end']
    ) for booking in data]

    cmd = 'INSERT INTO RoomBookings("bookingType", "name", "roomId", "start", "end") VALUES (%s, %s, %s, %s, %s)'
    cursor.executemany(cmd, values)


if __name__ == '__main__':
    try:
        connection = psycopg2.connect(user="postgres",
                                      password="postgrespassword",
                                      host="127.0.0.1",
                                      port="5432",
                                      database="postgres")
        cursor = connection.cursor()

        insert_buildings(cursor)
        connection.commit()

        insert_rooms(cursor)
        connection.commit()

        insert_bookings(cursor)
        connection.commit()
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
