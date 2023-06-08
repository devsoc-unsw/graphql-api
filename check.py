import json
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv
import docker
from docker.types import Mount

def insert_buildings(cursor):
    with open('output/nss-scraper/buildings.json') as f:
        data = json.load(f)
    values = [(bldg['id'], bldg['name'], bldg['lat'], bldg['long']) for bldg in data]

    cmd = 'INSERT INTO Buildings("id", "name", "lat", "long") VALUES (%s, %s, %s, %s)'
    cursor.executemany(cmd, values)


def insert_rooms(cursor):
    with open('output/nss-scraper/rooms.json') as f:
        data = json.load(f)
    values = [(
        room['id'],
        room['name'],
        room['abbr'],
        room['usage'],
        room['capacity'],
        room['school'],
        '-'.join(room['id'].split('-')[:2])
    ) for room in data]

    cmd = 'INSERT INTO Rooms("id", "name", "abbr", "usage", "capacity", "school", "buildingId") VALUES (%s, %s, %s, %s, %s, %s, %s)'
    cursor.executemany(cmd, values)


def insert_bookings(cursor):
    with open('output/nss-scraper/bookings.json') as f:
        data = json.load(f)
    values = [(
        booking['type'],
        booking['name'],
        booking['roomId'],
        booking['start'],
        booking['end']
    ) for booking in data]

    cmd = 'INSERT INTO Bookings("bookingType", "name", "roomId", "start", "end") VALUES (%s, %s, %s, %s, %s)'
    cursor.executemany(cmd, values)


if __name__ == '__main__':
    connection = None
    cursor = None
    load_dotenv()
    client = docker.from_env()
    client.login(
        username=os.environ.get('DOCKER_REGISTRY_USER'),
        password=os.environ.get('DOCKER_REGISTRY_PASSWORD'),
        registry=os.environ.get('DOCKER_REGISTERY_URL')
    )
    container = client.containers.run(
        os.environ.get('DOCKER_REGISTRY_USER') + "/nss-scraper-scraper",
        mounts=[Mount("/app/output", os.getcwd() + "/output/nss-scraper", 'bind')]
    )
    try:
        connection = psycopg2.connect(user=os.environ.get('POSTGRES_USER'),
                                      password=os.environ.get('POSTGRES_PASSWORD'),
                                      host="postgres",
                                      port=os.environ.get('POSTGRES_PORT'),
                                      database=os.environ.get('POSTGRES_DB'))
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
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
