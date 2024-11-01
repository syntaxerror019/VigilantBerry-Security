import cv2, numpy

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
    
    def generate_fallback(self, width, height, text="No signal"):
        frame = cv2.cvtColor(numpy.random.randint(0, 256, (height, width), dtype=numpy.uint8), cv2.COLOR_GRAY2BGR)
        font, scale, color, thickness = cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        x, y = (width - text_size[0]) // 2, (height + text_size[1]) // 2
        cv2.rectangle(frame, (x - 10, y - text_size[1] - 10), (x + text_size[0] + 10, y + 10), (0, 0, 0), cv2.FILLED)
        cv2.putText(frame, text, (x, y), font, scale, color, thickness)
        return frame

    def reset_capture(self):
        self.camera = cv2.VideoCapture(self.camera_id)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.dimensions[0]))
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.dimensions[1]))
    
    def release(self):
        self.camera.release()
    