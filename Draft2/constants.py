from socket import *

ranks_map = {
        "A":11,
        "7":10,
        "K":4,
        "J":3,
        "Q":2,
        "2":0,
        "3":0,
        "4":0,
        "5":0,
        "6":0
    }

suits = ["H", "D", "C", "S"]


BYTESIZE = 1024
ENCODER = 'utf-8'
PORT = 12345
ID = gethostbyname(gethostname())
CONNECT_INFO = (ID,PORT)