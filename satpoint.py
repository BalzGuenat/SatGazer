import time
import requests as rq
import json
import numpy as np
from numpy.linalg import norm
from motor import Motor

# The coordinates (latitude, longitude) of the satpointer
LOCATION = 47, 8
# Altitude above sea level, in meters
ALTITUDE = 400
N2YO_API_KEY = open('api.key', 'r').readline()
EARTH_RADIUS = 6371000

HEADING_MOTOR_STEP_PIN = 1
HEADING_MOTOR_DIR_PIN = 2
ALTITUDE_MOTOR_STEP_PIN = 3
ALTITUDE_MOTOR_DIR_PIN = 4
MOTOR_STEP_SIZE = 360 / 512


def geo_to_euclid(coords):
    """transforms a set of coordinates (latitude, longitude, radius) to a vector."""
    lat, long = np.radians(coords[0]), np.radians(coords[1])
    v = np.array([np.cos(lat) * np.cos(long),
                  np.cos(lat) * np.sin(long),
                  np.sin(lat)])
    return v * coords[2]


def euclid_to_geo(v):
    """transforms a vector into a set of coordinates and a radius."""
    x, y, z = v[0], v[1], v[2]
    lat = np.arctan(z / np.sqrt(x ** 2 + y ** 2))
    lat = np.degrees(lat)
    long = np.arctan2(y, x)
    long = np.degrees(long)
    rad = np.linalg.norm(v)
    return lat, long, rad


def ground_basis(ground):
    """creates a basis from the location of the satpointer, given as a vector.
    b0 will point east
    b1 will point north
    b2 will point up, aligning with the location vector
    """
    y = np.array([0, 0, 1])
    ground = ground / norm(ground)
    north = y - ground * np.dot(y, ground)
    north = north / norm(north)
    east = np.cross(north, ground)
    east = east / norm(east)
    basis = np.array([east, north, ground])
    return basis


# time when locations were last fetched
fetch_time = 0
positions = []
FUTURE_SECONDS_TO_FETCH = 120
def current_sat_location():
    """Returns the current location of the tracked satellite as a vector."""
    global positions, fetch_time
    # millis = int(round(time.time() * 1000))
    # lat = (millis / 100 % 180) - 90
    # long = millis / 100 % 360
    # return geo_to_euclid(40, long, 1.2)
    now = int(time.time())
    pos_idx = now - fetch_time
    if len(positions) <= pos_idx:
        update_positions()
        pos_idx = int(time.time()) - fetch_time
    lat = positions[pos_idx]['satlatitude']
    long = positions[pos_idx]['satlongitude']
    rad = EARTH_RADIUS + positions[pos_idx]['sataltitude'] * 1000
    ele = positions[pos_idx]['elevation']
    azi = positions[pos_idx]['azimuth']
    # print('received: elevation: {}, azimuth: {}'.format(ele, azi))
    return lat, long, rad


def update_positions():
    global positions
    global fetch_time
    rsp = fetch_sat_loc()
    data = json.loads(rsp.text)
    positions = data['positions']
    fetch_time = int(time.time())
    print('updated positions')


def fetch_sat_loc():
    satid = 25544
    seconds = FUTURE_SECONDS_TO_FETCH
    url = 'https://www.n2yo.com/rest/v1/satellite/positions/{}/{}/{}/{}/{}/&apiKey={}'\
        .format(satid, LOCATION[0], LOCATION[1], ALTITUDE, seconds, N2YO_API_KEY)
    rsp = rq.get(url)
    return rsp


def sat_location_from_ground(ground, sat):
    """Returns the current location of the tracked satellite in the basis of the satpointer.
    ground and sat are given as vectors in the normal basis.
    """
    basis = ground_basis(ground)
    # Qi transforms vectors of the normal basis into the ground basis
    Qi = np.transpose(np.linalg.inv(basis))
    vec = sat - ground
    return Qi @ vec


class SatGazer:
    def __init__(self, hdg_stp, hdg_dir, alt_stp, alt_dir):
        self.mot_hdg = Motor(hdg_stp, hdg_dir, MOTOR_STEP_SIZE)
        self.mot_alt = Motor(alt_stp, alt_dir, MOTOR_STEP_SIZE)

    def __str__(self):
        return "SatGazer(H:{} A:{})".format(self.mot_hdg, self.mot_alt)

    def calibrate(self):
        self.mot_hdg.calibrate()
        self.mot_alt.calibrate()

    def pos(self, heading, altitude):
        self.mot_hdg.pos(heading)
        self.mot_alt.pos(altitude)


if __name__ == "__main__":
    ground = geo_to_euclid((LOCATION[0], LOCATION[1], EARTH_RADIUS + ALTITUDE))
    gazer = SatGazer(HEADING_MOTOR_STEP_PIN, HEADING_MOTOR_DIR_PIN,
                     ALTITUDE_MOTOR_STEP_PIN, ALTITUDE_MOTOR_DIR_PIN)
    while True:
        sat = current_sat_location()
        sat_vec = geo_to_euclid(sat)
        sat_ground = sat_location_from_ground(ground, sat_vec)
        lat, long, dist = euclid_to_geo(sat_ground)
        # we want the angle from north-heading but have the angle from east-heading.
        heading = (-long + 90) % 360
        print("Pitch: {:3.0f}°, Heading: {:3.0f}°, Dist: {:5.2f}km".format(lat, heading, dist / 1000))
        # print("Lat: {}, Long: {}, Dist: {}".format(lat, long, dist))
        # we want the angle from "up" but have the angle from horizon.
        lat = 90 - lat
        gazer.pos(heading, lat)
        print(gazer)
        time.sleep(5)

