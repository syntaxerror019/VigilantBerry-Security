##################################################################
# Version 3.0 of CCTV Security System for RPi.
# This version will store all data locally on the device.
# This version also supports multiple cameras.
##################################################################
# Miles Hilliard - https://mileshilliard.com/ | https://sntx.dev/

import cv2, numpy, time, threading, os, logging, sys
from flask import Flask, render_template, redirect, request, url_for, jsonify, Response, send_file
from datetime import datetime, timedelta
from functools import wraps
from camera import Camera
import json
import psutil
import subprocess
from pathlib import Path
from datetime import timedelta
import socket
import re

app = Flask(__name__)

default_path = os.path.join(app.root_path, "static", "footage")
snapshots = os.path.join(app.root_path, "static", "snapshots")

directory = app.root_path

listed_cameras = []
camera_frames = {}
writers = {}

kill = False

if not os.path.exists(default_path):
    os.makedirs(default_path)

if not os.path.exists(snapshots):
    os.makedirs(snapshots)

SNAPSHOTS = snapshots
LOCATION = default_path
SETTINGS = Path(__file__).resolve().parent / "settings.json"
VERSION = None
VIRGIN = None
NAME = None
MODE = None
IP = None

# Recording and livestream resolution
# This does not affect the resolution of the frames being taken from the camera.
# This DOES affect the resolution of the frames being saved to the disk.
DISPLAY_HEIGHT = 480
DISPLAY_WIDTH = 640

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# displayed on dashboard.
def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "Unable to get IP address"

# TODO: Re-make this
def restart_script() -> None:
    logging.info("Restarting script...")
    set_kill_flag(True)
    time.sleep(3) # TODO: Make this more elegant
    set_kill_flag(False)
    setup()

def set_kill_flag(state: bool):
    global kill
    kill = state

def default_settings() -> dict:
    default_settings = {
            "version": "3.6.6",
            "virgin": True,
            "debug": False,
            "name": "vberry",
            "connectivity": "client",
            "record_path": "",
            "settings": {
                "monitor.cameras": [
                ]
            }
        }
    write_settings(default_settings)
    return default_settings

# read json settings. if not available, use predefined.
def read_settings() -> dict:
    if not SETTINGS.exists():
        return default_settings()
    
    try:
        with open(SETTINGS, "r") as f:
            content = f.read().strip()
            if not content:
                return default_settings()
            return json.loads(content)
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from settings file.")
        return default_settings()

# save to disk.
def write_settings(settings) -> None:
    with open(SETTINGS, "w") as file:
        json.dump(settings, file, indent=4)

# modify var in cam settings... TODO: make more elegant
def update_camera_entry(camera_statuses, target_index, updates) -> None:
    for status in camera_statuses:
        if status['index'] == target_index:
            status.update(updates)
            break

# TODO: Add support for more OS. Works with RPi OS. Does not with RPi Ubuntu Server!
def get_cpu_usage() -> float:
    return psutil.cpu_percent(interval=1)

def get_memory_usage() -> int:
    mem = psutil.virtual_memory()
    return int(mem.percent)

def get_disk_usage() -> dict:
    disk = psutil.disk_usage('/')
    return {
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent,
    }

def get_temperature() -> str:
    try:
        if os.path.exists('/usr/bin/vcgencmd'):
            temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            return temp_output.strip().split('=')[1]  # e.g., '45.0\'C'
        
        if os.path.exists('/usr/bin/sensors'):
            temp_output = subprocess.check_output(['sensors']).decode()
            # Find temperature line
            for line in temp_output.splitlines():
                if 'temp' in line:
                    return line.strip()
        
        return "temp cmd not available."
    
    except Exception as e:
        return str(e)

# not sure how supported this is across OS but it works for Ubuntu Server and RPI os.
def get_uptime() -> str:
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])

    uptime = str(timedelta(seconds=uptime_seconds))
    return uptime

# Show connected USB cameras.
def list_cameras() -> list:
    available_cameras = []
    for index in range(10):  # Check first 10 indices
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            camera_info = {
                "index": index,
                "name": f"Camera {index}",
                "frame_width": cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                "frame_height": cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                "fps": cap.get(cv2.CAP_PROP_FPS)
            }
            available_cameras.append(camera_info)
        cap.release()
    return available_cameras

def directory_check(directory) -> None:
    if not os.path.exists(directory):
        os.makedirs(directory)

def text_overlay(frame, text) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    color = (255, 255, 255)  # White color
    thickness = 2

    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]

    text_x = 10
    text_y = int(DISPLAY_HEIGHT) - 10

    cv2.rectangle(frame,  # black textbox white text
                (text_x - 5, text_y - text_size[1] - 5), 
                (text_x + text_size[0] + 5, text_y + 5), 
                (0, 0, 0), 
                cv2.FILLED)

    cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)

def format_overlay(camera_name) -> str:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{current_datetime} | {camera_name}"

def remove_files(folder, age, ctime, extension) -> None:
    for file in os.listdir(folder):
        if file.endswith(extension):
            file_path = os.path.join(folder, file)
            file_time = os.path.getctime(file_path)
            if ctime - file_time >= age * 60:
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")

def recording_function(cameras, objs, check_interval=5) -> None:
    """Recording thread for each all cameras with optimized CPU usage."""

    current_datetime = datetime.now()
    
    for camera in cameras:
        directory_check(f"{SNAPSHOTS}/{camera['name']}")
        directory_check(f"{LOCATION}/{camera['name']}")

        folder = os.path.join(LOCATION, camera['name'])
        camera['folder'] = folder  

        filename = os.path.join(camera['folder'], f"{camera['name']}_{current_datetime.strftime('%Y-%m-%d_%H-%M-%S')}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = camera["fps"]
        size = (DISPLAY_WIDTH, DISPLAY_HEIGHT)

        writers[camera["index"]] = cv2.VideoWriter(filename, fourcc, fps, size)
        camera["start_time"] = time.time()

        # File cleanup every 'check_interval' minutes
        last_cleanup_time = time.time()
        cleanup_interval = check_interval * 60
    try:
        while not kill:
                current_time = time.time()

                for camera, obj in zip(cameras, objs):
                    if current_time - camera["start_time"] >= camera["duration"] * 60:
                        writers[camera["index"]].release()
                        current_datetime = datetime.now()
                        filename = os.path.join(camera["folder"], f"{camera['name']}_{current_datetime.strftime('%Y-%m-%d_%H-%M-%S')}.mp4")
                        writers[camera["index"]] = cv2.VideoWriter(filename, fourcc, fps, size)
                        camera["start_time"] = current_time
                    
                    frame = obj.read_frame()
                
                    if frame is None:
                        obj.reset_capture()
                        frame = obj.generate_fallback(640, 480, "No signal")
                    else:
                        frame = cv2.resize(frame, (640, 480))

                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                    if 'background' not in camera or 'motion_counter' not in camera or 'last_snapshot_time' not in camera:
                        camera['background'] = gray_frame
                        camera['motion_counter'] = 0
                        camera['last_snapshot_time'] = 0
                        continue

                    frame_delta = cv2.absdiff(camera['background'], gray_frame)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

                    thresh = cv2.dilate(thresh, None, iterations=2)
                    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    motion_detected = False
                    min_x, min_y = frame.shape[1], frame.shape[0]
                    max_x, max_y = 0, 0

                    for contour in contours:
                        if cv2.contourArea(contour) < 700:
                            continue

                        (x, y, w, h) = cv2.boundingRect(contour)
                        min_x, min_y = min(min_x, x), min(min_y, y)
                        max_x, max_y = max(max_x, x + w), max(max_y, y + h)
                        motion_detected = True

                    if motion_detected:
                        camera['motion_counter'] += 1
                    else:
                        camera['motion_counter'] = 0

                    if camera['motion_counter'] >= 10:
                        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), (0, 255, 0), 2)
                        # Save snapshot if 5 seconds have passed since the last snapshot
                        current_time = time.time()
                        if current_time - camera['last_snapshot_time'] >= 5:
                            snapshot_folder = os.path.join(SNAPSHOTS, camera['name'])
                            snapshot_filename = os.path.join(snapshot_folder, f"{camera['name']}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg")
                            cv2.imwrite(snapshot_filename, frame)
                            camera['last_snapshot_time'] = current_time

                    # Update the background frame
                    camera['background'] = gray_frame

                    text_overlay(frame, format_overlay(camera["name"]))

                    writers[camera["index"]].write(frame)
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    
                    if ret:
                        camera_frames[camera["index"]] = jpeg.tobytes()


                if current_time - last_cleanup_time >= cleanup_interval:
                    for camera in cameras:
                        age = camera["age"]

                        # remove snapshots and video files
                        remove_files(camera["folder"], age, current_time, ".mp4")
                        remove_files(os.path.join(SNAPSHOTS, camera["name"]), age, current_time, ".jpg")

                    last_cleanup_time = current_time
    except KeyboardInterrupt:
        set_kill_flag(True)

    # clean up writers and camera objects
    for camera, obj in zip(cameras, objs):
        writers[camera["index"]].release()
        obj.release()

    logging.info(f"Recording stopped.")

def get_files(cameras, folder_base, extension):
    files = {}
    for camera in cameras:
        folder = os.path.join(folder_base, camera['name'])
        if not os.path.exists(folder):
            return redirect(url_for("setup_web"))
        files[camera['name']] = sorted(
            [file for file in os.listdir(folder) if file.endswith(extension)],
            key=lambda x: os.path.getctime(os.path.join(folder, x)),
            reverse=True
        )
    return files

def initialize_cameras(cameras) -> tuple:
    """ Initialize cameras based on the settings. """

    camera_objects = []

    for camera in cameras:
        logging.info(f"Initializing camera {camera['index']} ({camera['frame_width']}x{camera['frame_height']})...")

        cam = Camera(camera["index"], camera["fps"], (camera["frame_width"], camera["frame_height"]))
        camera_objects.append(cam)

        logging.info(f"Camera {camera['index']} ({camera['frame_width']}x{camera['frame_height']}) initialized.")

    return True, camera_objects
              

def setup() -> None:
    """ Setup function to initialize and start everything. """

    print("""
            ┓┏•  •┳┓        
            ┃┃┓┏┓┓┣┫┏┓┏┓┏┓┓┏
            ┗┛┗┗┫┗┻┛┗ ┛ ┛ ┗┫
                ┛          ┛
            """)
    print("--- VigilantBerry | 2024 | https://sntx.dev/ ---\n")

    global LOCATION, VERSION, VIRGIN, NAME, MODE, IP, listed_cameras
    settings = read_settings()
    cameras = list_cameras()

    if not cameras:
        logging.critical("No cameras found.")
        logging.critical("exiting...")
        sys.exit()
    
    listed_cameras = cameras

    logging.info("External modules imported.")
    
    if settings is None:
        logging.warning("Settings file not found.")
        logging.warning("Please be sure all files are present and in the correct location.")
        logging.warning("exiting...")
        sys.exit()
        
    logging.info("Settings file loaded.")

    VERSION = settings.get("version", VERSION)
    VIRGIN = settings.get("virgin", VIRGIN)
    NAME = settings.get("name", NAME)
    MODE = settings.get("connectivity", MODE)
    debug = settings.get("debug", False)

    if not VIRGIN:
        LOCATION = settings.get("record_path", LOCATION)

    IP = get_local_ip()

    if VIRGIN:
        logging.info("Virgin mode detected.")
        logging.info("Starting setup...")
        return

    if not debug:
        camera_ok, objects = initialize_cameras(settings["settings"]["monitor.cameras"])
        
        if not camera_ok:
            logging.warning("An error was reported in the initialization phase.")
            logging.warning("exiting...")
            sys.exit()

        recording_function(settings["settings"]["monitor.cameras"],objects)
    else:
        logging.info("Debug mode detected.")
        logging.info("Starting debug mode...")
        

###### Flask Endpoints ######

# Decorator to check if the system is in first-time setup mode.
def virgin_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if VIRGIN:
            return redirect(url_for('setup_web'))  # Redirects to the "redirected" route if the flag is true
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@virgin_check
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@virgin_check
def dashboard():
    global listed_cameras

    cameras = read_settings()["settings"]["monitor.cameras"]

    video_files = get_files(cameras, LOCATION, ".mp4")
    pictures = get_files(cameras, SNAPSHOTS, ".jpg")

    return render_template("index.html", cpu=get_cpu_usage(), memory=get_memory_usage(), disk=get_disk_usage(), temp=get_temperature(), uptime=get_uptime(), cameracount=len(cameras), cameras=cameras, VERSION=VERSION, NAME=NAME, MODE=MODE, IP=IP, available_device_change=0, video_files=video_files, pictures=pictures)

@app.route("/kill")
def kill_all():
    global kill
    kill = True
    time.sleep(1) # TODO: Make this more elegant

    # Terminate all threads
    for thread in threading.enumerate():
        if thread is not threading.current_thread():
            try:
                thread.join(timeout=1)
                print(f"Thread {thread.name} terminated.")
            except Exception as e:
                logging.error(f"Error terminating thread {thread.name}: {e}")

    logging.info("All threads terminated. Exiting application.")
    os._exit(0)

@app.route("/alive", methods=["GET", "POST"])
def alive():
    return jsonify({"status": "success", "message": "System is alive."}), 200

@app.route("/download/<string:camera_name>/<string:file_name>")
@virgin_check
def download(camera_name, file_name):
    file_path = os.path.join(LOCATION, camera_name, file_name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found."}), 404
    
@app.route("/view/<string:camera_name>/<string:file_name>")
@virgin_check
def view(camera_name, file_name):
    video_path = os.path.join(LOCATION, camera_name, file_name)

    if os.path.exists(video_path):
        range_header = request.headers.get('Range', None)
        if not range_header:
            return send_file(video_path)

        size = os.path.getsize(video_path)
        byte1, byte2 = 0, None

        m = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if m:
            g = m.groups()
            byte1 = int(g[0])
            if g[1]:
                byte2 = int(g[1])

        byte2 = byte2 if byte2 is not None else size - 1
        length = byte2 - byte1 + 1

        with open(video_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        resp = Response(data, 206, mimetype='video/mp4', content_type='video/mp4')
        resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(length))
        return resp
    
    else:
        return jsonify({"status": "error", "message": "File not found."}), 404

@app.route('/video_feed/<int:camera_index>')
@virgin_check
def video_feed(camera_index):
    """Video streaming route. Returns the video feed for the given camera index."""
    def generate(camera_index):
        while True:
            frame = camera_frames.get(camera_index, None)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                time.sleep(0.1) # TODO: Make this more elegant

    return Response(generate(camera_index),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_camera/<int:camera_index>', methods=["POST"])
def save_camera_data(camera_index):
    settings = read_settings()
    cameras = settings["settings"]["monitor.cameras"]

    for camera in cameras:
        if camera["index"] == camera_index:
            camera["name"] = request.form.get("camera_name")
            camera["duration"] = float(request.form.get("camera_duration"))
            camera["age"] = float(request.form.get("camera_age"))
            camera["fps"] = float(request.form.get("camera_fps"))

            resolution = request.form.get("camera_resolution")

            # camera["frame_width"] = float(resolution.split("x")[0])
            # camera["frame_height"] = float(resolution.split("x")[1])
            
            break
    else:
        return jsonify({"status": "error", "message": "Camera not found."}), 404
    
    write_settings(settings)
    restart_script()

    return '', 204

@app.route("/camera_selection", methods=["POST"])
def update_camera_list():
    global VIRGIN
    settings = read_settings()
    cameras = list_cameras()
    selected_cameras = request.json["cameras"]

    for x, camera in enumerate(cameras):
        if str(camera["index"]) in selected_cameras:
            entry = {
                "index": camera["index"],
                "name": "Default_Camera_" + str(camera["index"]),
                "frame_width": 320,
                "frame_height": 240,
                "fps": camera["fps"],
                "duration": 60, # 60 minutes per recording
                "age": 4320 # 3 days of footage
            }
            settings["settings"]["monitor.cameras"].append(entry)
    
    settings["virgin"] = False
    VIRGIN = False

    write_settings(settings)
    setup()
    
    return jsonify({"status": "success", "message": "Cameras updated successfully."}), 200

@app.route("/footage_location", methods=["POST"])
def footage_save():
    settings = read_settings()
    path = request.json["path"]

    if not os.path.exists(path):
        return jsonify({"status": "error", "code": 400, "message": "Invalid path. Double check the integrity."}), 400
    
    settings["record_path"] = path
    write_settings(settings)

    return jsonify({"status": "success", "code": 200, "message": "Location updated successfully."}), 200

@app.route("/setup")
def setup_web():
    cameras = listed_cameras
    if not cameras:
        logging.critical("No cameras found.")
        return "<h1>No cameras found on the system.</h1><p>There were no usable cameras found on your system. Please check all connections and reload this page.</p>", 500
    
    return render_template("setup.html", cameras=cameras, default_location=LOCATION)

if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start() # TODO: Make this more elegant
    setup()
