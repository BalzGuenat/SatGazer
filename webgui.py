#!/usr/bin/python3

import http.server
import re
from satpoint import SatGazer, SatGazerDriver
from motor import UnipolarMotor
import abc
import json

PORT = 8000

# The coordinates (latitude, longitude) of the satpointer
LOCATION = 47, 8
# Altitude above sea level, in meters
ALTITUDE = 400
# the satellite ID
SAT_ID = 25544

landing = open("gui.html", "rb").read()
js = open("js.js", "rb").read()

pattern_track = re.compile("/track/(.+?)/(.+?)/(.+)")
pattern_driver = re.compile("/driver/(.+?)/(.+)")


class UrlHandler:
    def __init__(self, url_regex: str, callback: callable):
        self.url_regex = re.compile('^' + url_regex + '$')
        self.callback = callback

    def should_handle(self, request: http.server.BaseHTTPRequestHandler):
        return self.url_regex.match(request.path)

    @abc.abstractmethod
    def handle(self, request, m):
        self.callback(request, m)


def create_request_handler_class(gazer: SatGazer, driver: SatGazerDriver):
    handlers = []

    def _h_root(rq, m):
        rq.send_response(200)
        rq.send_header('Content-type', 'text/html')
        rq.end_headers()
        rq.wfile.write(landing)
    handlers.append(UrlHandler('/', _h_root))

    def _h_js_js(rq, m):
        rq.send_response(200)
        rq.send_header('Content-type', 'text/javascript')
        rq.end_headers()
        rq.wfile.write(js)
    handlers.append(UrlHandler('/js\\.js', _h_js_js))

    def _h_calibrate(rq, m):
        gazer.calibrate()
        rq.send_response(204)
        rq.end_headers()
    handlers.append(UrlHandler('/calibrate', _h_calibrate))

    def _h_coast(rq, m):
        gazer.stop_tracking()
        gazer.coast()
        rq.send_response(204)
        rq.end_headers()
    handlers.append(UrlHandler('/coast', _h_coast))

    def _h_track(rq, m):
        lat = float(m.group(1))
        long = float(m.group(2))
        sat_id = m.group(3)
        rq.send_response(200)
        rq.send_header('Content-type', 'text/html')
        rq.end_headers()
        rq.wfile.write('lat={}, long={}, sat_id={}'.format(lat, long, sat_id).encode())
        gazer.location = lat, long
        gazer.target = sat_id
        gazer.start_tracking()
    handlers.append(UrlHandler('/track/(.+?)/(.+?)/(.+)', _h_track))

    def _h_driver(rq, m):
        azi = float(m.group(1))
        alt = float(m.group(2))
        gazer.stop_tracking()
        driver.pos(azi, alt)
        rq.send_response(204)
        rq.end_headers()
    handlers.append(UrlHandler('/driver/(.+?)/(.+)', _h_driver))

    def _h_status(rq, m):
        stat = {
            'observer_latitude': gazer.location[0],
            'observer_longitude': gazer.location[1],
            'is_tracking': gazer.is_tracking(),
            'azimuth': gazer.azimuth,
            'zenith': gazer.zenith,
            'driver_azi': gazer.driver.azi,
            'driver_zen': gazer.driver.zen
        }
        if gazer.is_tracking():
            loc = gazer.sat_location()
            stat['target_id'] = gazer.target
            stat['target_latitude'] = loc[0]
            stat['target_longitude'] = loc[1]
            stat['target_altitude'] = loc[2]

        rq.send_response(200)
        rq.send_header('Content-type', 'application/json')
        rq.end_headers()
        rq.wfile.write(json.dumps(stat).encode())
    handlers.append(UrlHandler('/status', _h_status))

    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # print(self.path)
            for h in handlers:
                m = h.should_handle(self)
                if m:
                    h.handle(self, m)
                    return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    return RequestHandler


def start_server(gazer: SatGazer, driver: SatGazerDriver):
    srv = http.server.HTTPServer(('0.0.0.0', PORT), create_request_handler_class(gazer, driver))
    srv.serve_forever()


if __name__ == "__main__":
    mot_azi = UnipolarMotor(19, 13, 6, 5, 5.625 / 32)
    mot_alt = UnipolarMotor(22, 27, 17, 18, 5.625 / 32, reverse=True)
    mot_azi.name = 'AziMot'
    mot_alt.name = 'AltMot'
    driver = SatGazerDriver(mot_azi, mot_alt)
    gazer = SatGazer(driver)
    gazer.location = LOCATION
    gazer.target = SAT_ID
    # gazer.start_tracking()

    # def cb(lat, long, sat_id): print('lat={}, long={}, sat_id={}'.format(lat, long, sat_id))
    try:
        start_server(gazer, driver)
    except KeyboardInterrupt as i:
        gazer.stop_tracking()
        raise i
