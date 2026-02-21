import cv2

class Camera:
    COMMON_RESOLUTIONS = [
        (3840, 2160), (2560, 1440), (1920, 1080),
        (1280, 720), (1024, 576), (854, 480),
        (640, 480), (320, 240)
    ]

    def __init__(self, method='usb', index=0, url=None, video_file=None, resolution=None):
        self.method = method
        self.index = index
        self.url = url
        self.video_file = video_file
        self.resolution = resolution
        self.cap = None

    def open(self):
        print(f"[Camera] Abrindo câmera: método={self.method}, index={self.index}, url={self.url}, arquivo={self.video_file}")
        if self.method == 'usb':
            self.cap = cv2.VideoCapture(self.index)
        elif self.method == 'ip':
            self.cap = cv2.VideoCapture(self.url)
        elif self.method == 'file':
            self.cap = cv2.VideoCapture(self.video_file)
        else:
            raise ValueError("Método de acesso de câmera inválido.")

        if not self.cap.isOpened():
            raise RuntimeError("[Camera] Não foi possível abrir a câmera.")

        if self.resolution:
            print(f"[Camera] Tentando resolução desejada: {self.resolution}")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

        for width, height in self.COMMON_RESOLUTIONS:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if (actual_width, actual_height) == (width, height):
                self.resolution = (width, height)
                print(f"[Camera] Resolução aceita: {width}x{height}")
                break
        else:
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution = (actual_width, actual_height)
            print(f"[Camera] Usando fallback de resolução: {actual_width}x{actual_height}")

    def read(self):
        if self.cap is None:
            self.open()
        ret, frame = self.cap.read()
        if not ret:
            print("[Camera] Falha ao capturar frame.")
        return ret, frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
            print("[Camera] Câmera liberada.")

    @staticmethod
    def list_usb_cameras(max_cameras=20):
        available = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"[Camera] Câmera USB encontrada: {i}")
                available.append(i)
                cap.release()
        return available
