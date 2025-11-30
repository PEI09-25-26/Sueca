import unittest
from src.game_server import *
from unittest.mock import Mock,patch
from src.constants import *
import builtins
class TestGameServer(unittest.TestCase):


    def setUp(self):
        self.game_server = GameServer()


    def tearDown(self):
        self.game_server = None
if __name__ == "__main__":
    unittest.main()