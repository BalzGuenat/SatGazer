import http.server
import re
from satpoint import SatGazer, SatGazerDriver
from motor import UnipolarMotor

PORT = 8000

# The coordinates (latitude, longitude) of the satpointer
LOCATION = 47, 8
# Altitude above sea level, in meters
ALTITUDE = 400
# the satellite ID
SAT_ID = 25544

landing = open("gui.html", "rb").read()
js = open("js.js", "rb").read()

pattern = re.compile("/(.+?)/(.+?)/(.+)")


def create_request_handler_class(gazer: SatGazer):
    class RequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            print(self.path)
            if self.path == "/":
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(landing)
            if self.path == "/js.js":
                self.send_response(200)
                self.send_header('Content-type', 'text/javascript')
                self.end_headers()
                self.wfile.write(js)
            else:
                m = pattern.match(self.path)
                if m:
                    lat = int(m.group(1))
                    long = int(m.group(2))
                    sat_id = m.group(3)
                    self.send_response(200)
                    self.wfile.write('lat={}, long={}, sat_id={}'.format(lat, long, sat_id).encode())
                    gazer.location = lat, long
                    gazer.target = sat_id
                else:
                    self.send_response(404)
    return RequestHandler


def start_server(callback):
    srv = http.server.HTTPServer(('localhost', PORT), create_request_handler_class(callback))
    srv.serve_forever()


if __name__ == "__main__":
    mot_hdg = UnipolarMotor(18, 17, 22, 23, 5.625/32)
    mot_alt = UnipolarMotor(10, 11, 12, 13, 5.625/32)
    hw = SatGazerDriver(mot_hdg, mot_alt)
    gazer = SatGazer(hw)
    gazer.location = LOCATION
    gazer.target = SAT_ID
    gazer.start_tracking()

    # def cb(lat, long, sat_id): print('lat={}, long={}, sat_id={}'.format(lat, long, sat_id))
    start_server(gazer)

