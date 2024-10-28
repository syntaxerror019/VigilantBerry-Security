import cv2

class Camera:
    def __init__(self, camera_id, fps, dimensions):
        self.camera_id = camera_id
        self.fps = fps
        self.dimensions = dimensions
        self.camera = cv2.VideoCapture(camera_id)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.dimensions[0]))
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.dimensions[1]))
        
    def is_opened(self):
        return self.camera.isOpened()

    def read_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            print("Error: Could not read frame")
            return None
        return frame

    def reset_capture(self):
        self.camera = cv2.VideoCapture(self.camera_id)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.dimensions[0]))
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.dimensions[1]))
    
    def release(self):
        self.camera.release()
    