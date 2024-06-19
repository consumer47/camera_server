import threading
from camera_args import load_camera_configs, load_active_camera_names, get_active_camera_configs
from pi_camera_streamer import start_picamera_stream
from usb_camera_streamer import CameraStreamer, start_usb_stream
import cv2


def start_camera_stream(config):
    # Map the rotation argument to the corresponding OpenCV rotation code
    rotation_mapping = {
        0: None,
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE
    }
    rotation = rotation_mapping.get(config['rotation'], None)

    # Create a CameraStreamer instance for each camera configuration
    streamer = CameraStreamer(config['resolution'], rotation, config['port'])
    streamer.start_streaming()

if __name__ == "__main__":
    all_configs = load_camera_configs()  # Function to load camera configurations
    active_names = load_active_camera_names()  # Function to load active camera names
    active_configs = get_active_camera_configs(all_configs, active_names)  # Function to get active camera configs
    picamera_used = 0

    # Create a thread for each active camera configuration
    threads = []
    for config in active_configs:
        if config['type'] == 'usbcamera':
            thread = threading.Thread(target=start_camera_stream, args=(config,))
            threads.append(thread)
            thread.start()
        elif config['type'] == 'picamera':
            picamera_used+=1
            if (picamera_used > 1):
                print("Too many Picameras configured!!! Skipping config!", config)
                break
            thread = threading.Thread(target=start_picamera_stream, args=(config,))
            threads.append(thread)
            thread.start()
        else:
            raise ValueError(f"Unknown camera type: {config['type']}")

    # Wait for all threads to complete
    for thread in threads:
        thread.join()