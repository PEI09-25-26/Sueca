from socket import *
import os

"""Important constants shared among the other remaining classes. """

ranks_map = {
    "A": 11,
    "7": 10,
    "K": 4,
    "J": 3,
    "Q": 2,
    "2": 0,
    "3": 0,
    "4": 0,
    "5": 0,
    "6": 0,
}

suits = ["♡", "♢", "♣", "♠"]

BYTESIZE = 1024
ENCODER = "utf-8"
PORT = int(os.getenv("SUECA_PORT", "12345"))
SERVER_BIND = (os.getenv("SUECA_BIND", "0.0.0.0"), PORT)
DEFAULT_SERVER_IP = os.getenv("SUECA_SERVER_IP", gethostbyname(gethostname()))
CONNECT_INFO = (DEFAULT_SERVER_IP, PORT)
