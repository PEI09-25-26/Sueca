import logging
from color_formatter import ColorFormatter


class GameLogger:
    def __init__(self):
        self.logger = logging.getLogger(name="game_logger")
        self.fmt = (
            "%(asctime)s | "
            "%(lineno)4d | "          
            "%(levelname)-8s | "     
            "%(funcName)-30s | "      
            "%(message)s"
        )


        self.logger.setLevel(logging.DEBUG)

        self.file_handler = logging.FileHandler(filename="game.log", mode="w")
        self.stream_handler = logging.StreamHandler()

        self.file_handler.setLevel(logging.DEBUG)
        self.stream_handler.setLevel(logging.DEBUG)

        self.formatter = logging.Formatter(self.fmt)
        self.file_handler.setFormatter(self.formatter)
        self.stream_handler.setFormatter(ColorFormatter(
            self.fmt
        ))

        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.stream_handler)

    def log_debug(self, message):
        self.logger.debug(message, stacklevel=2)

    def log_info(self, message):
        self.logger.info(message, stacklevel=2)

    def log_warning(self, message):
        self.logger.warning(message, stacklevel=2)

    def log_error(self, message):
        self.logger.error(message, stacklevel=2)
