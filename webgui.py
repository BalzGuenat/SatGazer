import http.server
import re

PORT = 8000


landing = open("gui.html", "rb").read()
js = open("js.js", "rb").read()

pattern = re.compile("/(.+?)/(.+?)/(.+)")

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
                lat = m.group(1)
                long = m.group(2)
                sat_id = m.group(3)
                self.send_response(200)
                self.wfile.write('lat={}, long={}, sat_id={}'.format(lat, long, sat_id).encode())
            else:
                self.send_response(404)


srv = http.server.HTTPServer(('localhost', PORT), RequestHandler)
srv.serve_forever()