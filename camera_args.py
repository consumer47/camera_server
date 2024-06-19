# camera_args.py
import argparse

import json
import threading



# the new config based variant:
def load_camera_configs(config_file='all_cameras.json'):
    with open(config_file, 'r') as file:
        configs = json.load(file)
    return configs

def load_active_camera_names(active_config_file='active_cameras.json'):
    with open(active_config_file, 'r') as file:
        active_config = json.load(file)
    return active_config.get('active_cameras', [])

def get_active_camera_configs(all_configs, active_names):
    return [config for config in all_configs if config['name'] in active_names]

# the old arg based variant
def parse_camera_arguments():
    parser = argparse.ArgumentParser(description='Stream video from a selected camera source.')
    parser.add_argument('--camera', type=str, choices=['picamera', 'usbcamera'], required=False, help='Select the camera source to stream from. Default is the non-usb picamera.')
    parser.add_argument('--resolution', type=str, default='640x480', choices=['640x480', '800x600', '1024x768', '1280x720', '1920x1080'], help='Set the resolution of the video stream.')
    parser.add_argument('--rotation', type=int, default=0, choices=[0, 90, 180, 270], help='Rotate the camera view in degrees.')
    parser.add_argument('--port', type=int, default=8000, help='Set the port for the streaming server.')
    args = parser.parse_args()
    return args