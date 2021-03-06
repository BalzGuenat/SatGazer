import time
import requests as rq
import json
import numpy as np
from numpy.linalg import norm
from motor import Motor, UnipolarMotor
import threading
from typing import Tuple, Optional

# The coordinates (latitude, longitude) of the satpointer
LOCATION = 47, 8
# Elevation of the observer above sea level, in meters
# 194m is the estimated median elevation of a person's home
OBSERVER_ELEVATION = 408
# the sattelite ID
SAT_ID = 25544
N2YO_API_KEY = open('api.key', 'r').readline()
EARTH_RADIUS = 6371000

AZIMUTH_MOTOR_STEP_PIN = 1
AZIMUTH_MOTOR_DIR_PIN = 2
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


def current_sat_location(sat_id) -> Tuple[int, int, int]:
    """Returns the current location of the tracked satellite as a vector."""
    global positions, fetch_time
    # millis = int(round(time.time() * 1000))
    # lat = (millis / 100 % 180) - 90
    # long = millis / 100 % 360
    # return geo_to_euclid(40, long, 1.2)
    now = int(time.time())
    pos_idx = now - fetch_time
    if len(positions) <= pos_idx:
        update_positions(sat_id)
        pos_idx = int(time.time()) - fetch_time
    lat = positions[pos_idx]['satlatitude']
    long = positions[pos_idx]['satlongitude']
    rad = EARTH_RADIUS + positions[pos_idx]['sataltitude'] * 1000
    ele = positions[pos_idx]['elevation']
    azi = positions[pos_idx]['azimuth']
    # print('received: elevation: {}, azimuth: {}'.format(ele, azi))
    return lat, long, rad


def update_positions(sat_id):
    global positions
    global fetch_time
    rsp = fetch_sat_loc(sat_id)
    data = json.loads(rsp.text)
    positions = data['positions']
    fetch_time = int(time.time())
    print('updated positions')


def fetch_sat_loc(sat_id):
    seconds = FUTURE_SECONDS_TO_FETCH
    url = 'https://www.n2yo.com/rest/v1/satellite/positions/{}/{}/{}/{}/{}/&apiKey={}'\
        .format(sat_id, LOCATION[0], LOCATION[1], OBSERVER_ELEVATION, seconds, N2YO_API_KEY)
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


class SatGazerDriver:
    """
    SatGazer hardware driver
    """
    def __init__(self, mot_azi: Motor, mot_zen: Motor):
        """
        Creates a new SatGazer hardware driver
        :param mot_azi: the motor controlling the azimuth
        :param mot_zen: the motor controlling the zenitude
        """
        self.mot_azi = mot_azi
        self.mot_zen = mot_zen
        self.azi = 0
        self.zen = 0

    def __str__(self):
        return "SatGazer(H:{} A:{})".format(self.mot_azi, self.mot_zen)

    def calibrate(self):
        """
        Tell the SatGazer that is is aligned to the zero position,
        i.e. azimuth north and pointing straight towards the sky.
        """
        self.azi = 0
        self.zen = 0

    def coast(self):
        self.mot_azi.coast()
        self.mot_zen.coast()

    def pos(self, azimuth, zenith):
        """
        Moves the SatGazer to align with the specified angles
        :param azimuth: the azimuth in degrees. 0 is north and 90 is east.
        :param zenith: the zenith angle in degrees. 0 is up and 90 is level.
        """
        d_azi = (azimuth - self.azi) % 360

        # Instead of adjusting the azimuth more than 90 degrees, we just point backwards.
        # this is faster because of the gear reduction on the azimuth.
        if 90 < d_azi < 270:
            print("pointing backwards")
            d_azi = (d_azi + 180) % 360
            zenith = (-zenith) % 360
        # move from range [0,360] to [-180,180]
        if d_azi > 180:
            d_azi = d_azi - 360

        d_zen = (zenith - self.zen) % 360
        # move from range [0,360] to [-180,180]
        if d_zen > 180:
            d_zen = d_zen - 360

        # turn both motors in parallel
        # d_azi gets multiplied by 4 because the device has a 4x reduction on the azimuth.
        t = threading.Thread(target=lambda: (self.mot_azi.degrees(d_azi * 4), self.mot_azi.coast()))
        t.start()
        self.mot_zen.degrees(d_zen)
        self.mot_zen.coast()
        t.join()
        self.azi = self.azi + d_azi
        self.zen = self.zen + d_zen


class SatGazer:
    def __init__(self, driver: SatGazerDriver):
        self.driver = driver
        # the location as latitude and longitude
        self.loc = 0, 0
        self.azimuth = 0
        self.zenith = 0
        # the location as a vector. always computed from self.loc but cached because it rarely changes
        self.ground = geo_to_euclid((self.loc[0], self.loc[1], EARTH_RADIUS + OBSERVER_ELEVATION))
        self._target = None
        self.tracking_thread = None

    @property
    def location(self):
        return self.loc

    @location.setter
    def location(self, loc):
        global fetch_time
        assert -90 <= loc[0] <= 90
        loc = loc[0], loc[1] % 360
        print('New location: {}'.format(loc))
        self.loc = loc
        self.ground = geo_to_euclid((self.loc[0], self.loc[1], EARTH_RADIUS + OBSERVER_ELEVATION))
        # this forces a refetch the next time align is called
        fetch_time = 0
        if self.is_tracking():
            self.tracking_thread.align_now()

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, target):
        global fetch_time
        if target != self._target:
            print('New target: {}'.format(target))
            self._target = target
            # this forces a refetch the next time align is called
            fetch_time = 0

    def start_tracking(self):
        if self.is_tracking():
            self.tracking_thread.align_now()
        else:
            self.tracking_thread = Tracker(self)
            self.tracking_thread.start()

    def stop_tracking(self):
        if self.is_tracking():
            self.tracking_thread.stop()
            self.tracking_thread.join()

    def is_tracking(self):
        return bool(self.tracking_thread and self.tracking_thread.is_alive())

    def align(self) -> None:
        """
        Aligns to the target.
        """
        sat = current_sat_location(self.target)
        sat_vec = geo_to_euclid(sat)
        sat_ground = sat_location_from_ground(self.ground, sat_vec)
        lat, long, dist = euclid_to_geo(sat_ground)
        # we want the north-azimuth but have the angle from eastward.
        self.azimuth = (-long + 90) % 360
        # we want the zenith angle but have the angle from horizon.
        self.zenith = 90 - lat
        print("Zenith: {:3.0f}°, Azimuth: {:3.0f}°, Dist: {:5.2f}km"
              .format(self.zenith, self.azimuth, dist / 1000))
        print("Sat: Lat: {}, Long: {}, Alt: {}".format(sat[0], sat[1], sat[2]))
        self.driver.pos(self.azimuth, self.zenith)

    def calibrate(self) -> None:
        print("calibrating")
        self.azimuth = 0
        self.zenith = 0
        self.driver.calibrate()

    def coast(self) -> None:
        print("coasting")
        self.driver.coast()

    def sat_location(self) -> Tuple[int, int, int]:
        return current_sat_location(self.target)


class Tracker(threading.Thread):
    def __init__(self, gazer: SatGazer):
        super().__init__()
        self.gazer = gazer
        self._stop_event = threading.Event()
        self._stop_condition = threading.Condition()

    def run(self) -> None:
        self._stop_condition.acquire()
        while not self._stop_event.is_set():
            self.gazer.align()
            self._stop_condition.wait(1)
        self._stop_condition.release()

    def stop(self):
        self._stop_event.set()
        self._stop_condition.acquire()
        self._stop_condition.notify()
        self._stop_condition.release()

    def align_now(self):
        """
        Calls align immediately and resets the update period.
        """
        self._stop_condition.acquire()
        self._stop_condition.notify()
        self._stop_condition.release()


if __name__ == "__main__":
    mot_azi = UnipolarMotor(5, 6, 13, 19, 5.625/32)
    mot_alt = UnipolarMotor(17, 18, 27, 22, 5.625/32)
    hw = SatGazerDriver(mot_azi, mot_alt)
    gazer = SatGazer(hw)
    gazer.location = LOCATION
    gazer.target = SAT_ID
    # gazer.start_tracking()
