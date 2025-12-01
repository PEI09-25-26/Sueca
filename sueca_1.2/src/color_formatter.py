
import logging
class ColorFormatter(logging.Formatter):
    """This class is responsible for decorating the formatter class with colouring features. """
    COLORS = {
        'DEBUG': "\033[37m",
        'INFO': "\033[36m",
        'WARNING': "\033[33m",
        'ERROR': "\033[31m",
        'CRITICAL': "\033[41m"
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)

    