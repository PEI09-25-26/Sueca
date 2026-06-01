import cv2

class Camera:
    COMMON_RESOLUTIONS = [
        (3840, 2160),  
        (2560, 1440),  
        (1920, 1080),  
        (1280, 720),   
        (1024, 576),
        (854, 480),
        (640, 480),
        (320, 240)
    ]

    def __init__(self, method='usb', index=0, url=None, video_file=None, resolution=None):
        self.method = method
        self.index = index
        self.url = url
        self.video_file = video_file
        self.resolution = resolution
        self.cap = None

    def open(self):
        if self.method == 'usb':
            self.cap = cv2.VideoCapture(self.index)
        elif self.method == 'ip':
            self.cap = cv2.VideoCapture(self.url)
        elif self.method == 'file':
            self.cap = cv2.VideoCapture(self.video_file)
        else:
            raise ValueError("Método de acesso de câmera inválido.")

        if not self.cap.isOpened():
            raise RuntimeError("Não foi possível abrir a câmera.")

        if self.resolution:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if (actual_width, actual_height) == self.resolution:
                return

        for width, height in self.COMMON_RESOLUTIONS:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Check if the resolution is accepted by the camera
            if (actual_width, actual_height) == (width, height):
                print(f"Camera opened with resolution: {width}x{height}")
                self.resolution = (width, height)
                break
        else:
            # If none matched, fallback to whatever the camera supports
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution = (actual_width, actual_height)
            print(f"Using fallback camera resolution: {actual_width}x{actual_height}")

    def read(self):
        if self.cap is None:
            self.open()
        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    @staticmethod
    def list_usb_cameras(max_cameras=10):
        available = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
