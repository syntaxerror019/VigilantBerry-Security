import cv2, numpy, time, threading, os, logging, sys
from flask import Flask, render_template, redirect, request, url_for, jsonify, Response, send_file
from datetime import datetime
from camera import Camera
import json
from queue import Queue
from pathlib import Path
from datetime import timedelta
import socket
import re

##################################################################
# Version 3.0 of local security camera server.
# The previous versions utilized cloud or network based storage.
# This version will store all data locally on the device.
# This version also supports multiple cameras.
##################################################################
# Miles Hilliard - https://mileshilliard.com/ | https://sntx.dev/

app = Flask(__name__)

directory = app.root_path
default_path = os.path.join(app.root_path, "static", "footage")
snapshots = os.path.join(app.root_path, "static", "snapshots")
listed_cameras = []
kill = False

camera_frames = {}
writers = {}

if not os.path.exists(default_path):
    os.makedirs(default_path)

SNAPSHOTS = snapshots
LOCATION = default_path
VERSION = None
VIRGIN = None
NAME = None
MODE = None
IP = None

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def generate_fallback(width, height, text="No signal"):
    """ No Signal frame for the camera feed. """

    fallback_frame = numpy.random.randint(0, 256, (height, width), dtype=numpy.uint8)
    fallback_frame = cv2.cvtColor(fallback_frame, cv2.COLOR_GRAY2BGR)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2
    color = (255, 255, 255)  # White color
    thickness = 3

    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    # centered text pos
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    
    # black padded box around the text
    padding = 10
    cv2.rectangle(fallback_frame, 
                  (text_x - padding, text_y - text_size[1] - padding), 
                  (text_x + text_size[0] + padding, text_y + padding), 
                  (0, 0, 0), 
                  cv2.FILLED)
    
    # on top of no signal.
    cv2.putText(fallback_frame, text, (text_x, text_y), font, font_scale, color, thickness)
    
    return fallback_frame

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "Unable to get IP address"

def restart_script():
    """Restarts the current script."""

    logging.info("Restarting script...")

    global kill
    kill = True

    time.sleep(3) # Wait for threads to close TODO: Make this more elegant

    kill = False
    setup()

def read_settings():
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json")):
        default_settings = {
            "version": "3.6.6",
            "virgin": True,
            "debug": False,
            "name": "Camera Client 001",
            "connectivity": "client",
            "record_path": "",
            "settings": {
                "monitor.cameras": [
                ]
            }
        }
        write_settings(default_settings)
        return default_settings
    
    with open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "settings.json"), "r") as f:
        content = f.read()
        if content == "":
            return None
        return json.loads(content)

def write_settings(settings):
    with open("settings.json", "w") as file:
        json.dump(settings, file, indent=4)

def update_camera_entry(camera_statuses, target_index, updates):
    """
    Update the fields of a specific camera status entry.

    :param camera_statuses: List of camera status dictionaries.
    :param target_index: Index of the camera to update.
    :param updates: Dictionary of fields to update with their new values.
    """
    for status in camera_statuses:
        if status['index'] == target_index:
            status.update(updates)
            break


def list_cameras():
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

def recording_function(cameras, objs, check_interval=5):
    """Recording thread for each all cameras with optimized CPU usage."""

    current_datetime = datetime.now()

    for camera in cameras:
        folder = f"{LOCATION}/{camera['name']}"

        if not os.path.exists(folder):
            os.makedirs(folder)

        camera['folder'] = folder  

        filename = os.path.join(folder, f"{camera['name']}_{current_datetime.strftime('%Y-%m-%d_%H-%M-%S')}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = camera["fps"]
        size = (int(camera["frame_width"]), int(camera["frame_height"]))

        writers[camera["index"]] = cv2.VideoWriter(filename, fourcc, fps, size)

        camera["start_time"] = time.time()

        # File cleanup every 'check_interval' minutes
        last_cleanup_time = time.time()
        cleanup_interval = check_interval * 60

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
                if not hasattr(obj, 'fallback_counter'):
                    obj.fallback_counter = 0
                if obj.fallback_counter < 10:
                    frame = generate_fallback(int(camera["frame_width"]), int(camera["frame_height"]), "No input")
                else:
                    frame = generate_fallback(int(camera["frame_width"]), int(camera["frame_height"]), "Video loss")

                obj.fallback_counter += 1
                if obj.fallback_counter >= 20:
                    obj.fallback_counter = 0

                time.sleep(.1)

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
                    if not os.path.exists(snapshot_folder):
                        os.makedirs(snapshot_folder)
                    snapshot_filename = os.path.join(snapshot_folder, f"{camera['name']}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg")
                    cv2.imwrite(snapshot_filename, frame)
                    camera['last_snapshot_time'] = current_time

            # Update the background frame
            camera['background'] = gray_frame

            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            camera_name = camera["name"]
            display_text = f"{current_datetime} | {camera_name}"

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            color = (255, 255, 255)  # White color
            thickness = 2

            text_size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]

            text_x = 10
            text_y = int(camera["frame_height"]) - 10

            cv2.rectangle(frame,  # black textbox white text
                          (text_x - 5, text_y - text_size[1] - 5), 
                          (text_x + text_size[0] + 5, text_y + 5), 
                          (0, 0, 0), 
                          cv2.FILLED)

            cv2.putText(frame, display_text, (text_x, text_y), font, font_scale, color, thickness)

            writers[camera["index"]].write(frame)
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame = None

            if ret:
                camera_frames[camera["index"]] = jpeg.tobytes()

        if current_time - last_cleanup_time >= cleanup_interval:
            for camera in cameras:
                folder = camera["folder"]
                for file in os.listdir(folder):
                    if file.endswith(".mp4"):
                        file_path = os.path.join(folder, file)
                        file_time = os.path.getctime(file_path)
                        if current_time - file_time >= camera["age"] * 60:
                            os.remove(file_path)
                            logging.info(f"Deleted file: {file_path}")

                folder = os.path.join(SNAPSHOTS, camera["name"])
                for file in os.listdir(folder):
                    if file.endswith(".jpg"):
                        file_path = os.path.join(folder, file)
                        file_time = os.path.getctime(file_path)
                        if current_time - file_time >= camera["age"] * 60:
                            os.remove(file_path)
                            logging.info(f"Deleted file: {file_path}")

            last_cleanup_time = current_time

    for camera, obj in zip(cameras, objs):
        writers[camera["index"]].release()
        obj.release()

    logging.info(f"Recording stopped.")


def initialize_cameras(cameras) -> tuple:
    """ Initialize cameras based on the settings. """

    camera_objects = []

    is_ok = True

    for camera in cameras:
        logging.info(f"Initializing camera {camera['index']} ({camera['frame_width']}x{camera['frame_height']})...")

        cam = Camera(camera["index"], camera["fps"], (camera["frame_width"], camera["frame_height"]))

        """ 
        if not cam.is_opened():
            logging.critical(f"Camera {camera['index']} could not be initialized.")
            logging.critical("Cameras may have changed since the last settings were saved.")
            logging.critical(f"Available cameras: {list_cameras()}")
            logging.critical("exiting...")
            is_ok = False
            sys.exit() 
            """

        camera_objects.append(cam)

        logging.info(f"Camera {camera['index']} ({camera['frame_width']}x{camera['frame_height']}) initialized.")

    return is_ok, camera_objects
              

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

    LOCATION = settings.get("record_path") or LOCATION
    VERSION = settings.get("version") or VERSION
    VIRGIN = settings.get("virgin") or VIRGIN
    NAME = settings.get("name") or NAME
    MODE = settings.get("connectivity") or MODE
    debug = settings.get("debug") or False

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
        

#### Flask Endpoints ####


@app.route("/")
def index():
    if VIRGIN:
        return redirect(url_for("setup_web"))
    
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    global listed_cameras

    if VIRGIN:
        return redirect(url_for("setup_web"))

    cameras = read_settings()["settings"]["monitor.cameras"]

    # Get video files to be rendered on the dashboard page
    video_files = {}

    for camera in cameras:
        folder = os.path.join(LOCATION, camera['name'])
        if not os.path.exists(folder):
            return redirect(url_for("setup_web"))
        video_files[camera['name']] = sorted(
            [file for file in os.listdir(folder) if file.endswith(".mp4")],
            key=lambda x: os.path.getctime(os.path.join(folder, x)),
            reverse=True
        )

    # Get snapshots to be rendered on the dashboard page
    pictures = {}

    for camera in cameras:
        folder = os.path.join(SNAPSHOTS, camera['name'])
        if not os.path.exists(folder):
            return redirect(url_for("setup_web"))
        pictures[camera['name']] = sorted(
            [file for file in os.listdir(folder) if file.endswith(".jpg")],
            key=lambda x: os.path.getctime(os.path.join(folder, x)),
            reverse=True
        )

    return render_template("index.html", cameras=cameras, VERSION=VERSION, NAME=NAME, MODE=MODE, IP=IP, available_device_change=0, video_files=video_files, pictures=pictures)

@app.route("/kill")
def kill_all():
    global kill
    kill = True
    time.sleep(1)  # Wait for threads to close TODO: Make this more elegant

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

@app.route("/download/<string:camera_name>/<string:file_name>")
def download(camera_name, file_name):
    file_path = os.path.join(LOCATION, camera_name, file_name)
    print("FILE PATH: ", file_path)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found."}), 404
    
@app.route("/view/<string:camera_name>/<string:file_name>")
def view(camera_name, file_name):
    video_path = os.path.join(LOCATION, camera_name, file_name)
    print("FILE PATH: ", video_path)

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
def video_feed(camera_index):
    """Video streaming route. Returns the video feed for the given camera index."""
    def generate(camera_index):
        while True:
            frame = camera_frames.get(camera_index, None)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    return Response(generate(camera_index),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_camera/<int:camera_index>', methods=["POST"])
def save_camera_data(camera_index):
    settings = read_settings()
    cameras = settings["settings"]["monitor.cameras"]
    print("REQUEST", request.form)

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

    return redirect(url_for("dashboard"))

@app.route('/save_app', methods=["POST"])
def save_data(camera_index):
    settings = read_settings()
    print("REQUEST", request.json)

    var = request.json["variable"]
    val = request.json["value"]

    settings[var] = val

    return jsonify({"status": "success", "message": "Camera settings saved successfully."}), 200

    for camera in cameras:
        if camera["index"] == camera_index:
            camera["name"] = request.json["name"]
            camera["duration"] = request.json["duration"]
            camera["age"] = request.json["age"]
            break
    else:
        return jsonify({"status": "error", "message": "Camera not found."}), 404
    
    write_settings(settings)

    return jsonify({"status": "success", "message": "Camera settings saved successfully."}), 200

@app.route("/camera_selection", methods=["POST"])
def update_camera_list():
    global VIRGIN
    settings = read_settings()
    cameras = list_cameras()
    selected_cameras = request.json["cameras"]
    print("CAMERAS", selected_cameras)
    for x, camera in enumerate(cameras):
        print(camera["index"])
        if str(camera["index"]) in selected_cameras:
            print("Camera added.")
            entry = {
                "index": camera["index"],
                "name": "Default Camera " + str(camera["index"]),
                "frame_width": camera["frame_width"],
                "frame_height": camera["frame_height"],
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
    print("CAMERAS", cameras)
    if not cameras:
        logging.critical("No cameras found.")
        return "<h1>No cameras found on the system.</h1><p>There were no usable cameras found on your system. Please check all connections and reload this page.</p>", 500
    # if not VIRGIN:
    #    return redirect(url_for("/"))
    return render_template("setup.html", cameras=cameras, default_location=LOCATION)

if __name__ == "__main__":
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080}).start() # TODO: Make this more elegant
    setup()
