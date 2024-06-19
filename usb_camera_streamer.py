import cv2
from http import server
import socketserver
import threading
import time

class CameraStreamer:
    # Class-level set to keep track of camera indices that are in use
    cameras_in_use = set()
    cameras_in_use_lock = threading.Lock()

    @classmethod
    def list_available_cameras(cls, max_index=19):
        """
        List all available camera indices up to a specified max_index.
        """
        available_cameras = []
        for i in range(max_index):
            if i not in cls.cameras_in_use:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()
        return available_cameras

    def __init__(self, resolution, rotation, port):
        self.resolution = resolution
        self.rotation = rotation
        self.port = port
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.camera_idx = None

    def capture_frames(self):
        width, height = map(int, self.resolution.split('x'))
        camera = cv2.VideoCapture(self.camera_idx)
        if not camera.isOpened():
            raise ValueError(f"Error: Camera index {self.camera_idx} is not available.")

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Set the desired frame rate (fps)
        desired_frame_rate = 10  # for example, 10 fps
        frame_interval = 1.0 / desired_frame_rate  # interval between frames in seconds

        try:
            while True:
                start_time = time.time()  # Record the start time

                ret, frame = camera.read()
                if not ret:
                    print(f"Error: Can't receive frame from camera index {self.camera_idx}.")
                    break
                if self.rotation is not None:
                    frame = cv2.rotate(frame, self.rotation)
                with self.frame_lock:
                    self.latest_frame = frame

                # Wait until the frame interval has passed before capturing the next frame
                elapsed_time = time.time() - start_time
                time_to_wait = frame_interval - elapsed_time
                if time_to_wait > 0:
                    time.sleep(time_to_wait)
        finally:
            camera.release()
            with self.cameras_in_use_lock:
                self.cameras_in_use.remove(self.camera_idx)

    def start_streaming(self):
        available_cameras = self.list_available_cameras()
        print(f"Available cameras: {available_cameras}")

        # Try to start a stream with the first available camera that is not in use
        for camera_idx in available_cameras:
            with self.cameras_in_use_lock:
                if camera_idx in self.cameras_in_use:
                    continue  # Skip if the camera is already in use
                self.cameras_in_use.add(camera_idx)  # Mark this camera as in use
                self.camera_idx = camera_idx
                break
        else:
            print("No available cameras to start streaming.")
            return

        capture_thread = threading.Thread(target=self.capture_frames)
        capture_thread.daemon = True
        capture_thread.start()

        server_address = ('', self.port)
        server = ThreadedHTTPServer(server_address, StreamingHandler, self)
        print(f"MJPEG streaming at http://localhost:{self.port}/stream.mjpg")
        print(f"MJPEG streaming at http://pi-frontradar:{self.port}/stream.mjpg")

        server.serve_forever()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.camera_streamer = kwargs.pop('camera_streamer', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Age", 0)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
            )
            self.end_headers()

            while True:
                with self.camera_streamer.frame_lock:
                    if self.camera_streamer.latest_frame is None:
                        continue
                    frame_data = cv2.imencode(".jpg", self.camera_streamer.latest_frame)[1].tobytes()
                self.wfile.write(b"--FRAME\r\n")
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", len(frame_data))
                self.end_headers()
                self.wfile.write(frame_data)
                self.wfile.write(b"\r\n")
        else:
            self.send_error(404)
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, camera_streamer):
        self.camera_streamer = camera_streamer
        super().__init__(server_address, RequestHandlerClass)

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, camera_streamer=self.camera_streamer)

def start_usb_stream(config):
    # Map the rotation argument to the corresponding OpenCV rotation code
    rotation_mapping = {
        0: None,
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE
    }
    rotation = rotation_mapping.get(config['rotation'], None)

    streamer = CameraStreamer(config['resolution'], rotation, config['port'])
    streamer.start_streaming()