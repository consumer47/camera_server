#!/home/pi/kamen-street-pi/camera/my-env/bin/python3 
import io
import logging
import socketserver
from http import server
from threading import Condition
from PIL import Image

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from camera_args import load_camera_configs, load_active_camera_names
from typing import List
PAGE_TEMPLATE = """
<html>
<head>
<title>PiCamera Stream</title>
</head--system-site-packages>
<body>
<center><h1>PiCamera Stream</h1></center>
<center><img src="stream.mjpg" width="{width}" height="{height}"></center>
</body>
</html>
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

output = StreamingOutput()



class StreamingHandler(server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.config = kwargs.pop('config', None)  # Extract the config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/record/current.jpg':
            try:
                with output.condition:
                    output.condition.wait()
                    frame = output.frame
                if self.config['rotation'] == 0:
                    # usualy no rotation must be applied.
                    rotated_frame=frame
                else:
                    # Rotate the image using Pillow, based on the config rotation
                    # raw jpeg ->  pillow image -> rotation -> raw jpeg
                    image = Image.open(io.BytesIO(frame))
                    rotated_image = image.rotate(self.config['rotation'])  # Use the rotation from config
                    buf = io.BytesIO()
                    rotated_image.save(buf, format='JPEG')
                    rotated_frame = buf.getvalue()
                self.send_response(200)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-length', len(rotated_frame))
                self.end_headers()
                self.wfile.write(rotated_frame)
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame

                    if self.config['rotation'] == 0:
                        rotated_frame = frame
                    else:
                        # Rotate the image using Pillow, based on the config rotation
                        image = Image.open(io.BytesIO(frame))
                        rotated_image = image.rotate(self.config['rotation'])  # Use the rotation from config
                        buf = io.BytesIO()
                        rotated_image.save(buf, format='JPEG')
                        rotated_frame = buf.getvalue()
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(rotated_frame)))
                    self.end_headers()
                    self.wfile.write(rotated_frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, config):
        self.config = config
        super().__init__(server_address, RequestHandlerClass)

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, config=self.config)

def start_picamera_stream(config):
    resolution = tuple(map(int, config['resolution'].split('x')))
    port = config['port']

    picam2 = Picamera2()
    picam2_config = picam2.create_video_configuration(main={"size": resolution})
    picam2.configure(picam2_config)
    picam2.start_recording(JpegEncoder(), FileOutput(output))

    try:
        address = ('', port)
        server = StreamingServer(address, StreamingHandler, config)

        # Format the PAGE with the actual resolution
        global PAGE
        PAGE = PAGE_TEMPLATE.format(width=resolution[0], height=resolution[1])

        server.serve_forever()
    finally:
            picam2.stop_recording()


if __name__ == "__main__":
    config: List[dict] = load_camera_configs()
    picamera_list = [camera for camera in config if camera.get('type') == 'picamera']
    start_picamera_stream(picamera_list[0])
