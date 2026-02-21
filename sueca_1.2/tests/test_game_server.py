import unittest
from src.game_server import GameServer
from unittest.mock import Mock, patch
from src.positions import Positions
from src.player import Player
from src.constants import *

class TestGameServer(unittest.TestCase):

    def setUp(self):
        self.game_server = GameServer()
        if hasattr(self.game_server, 'server_socket') and self.game_server.server_socket is not None:
            self.game_server.server_socket.close()
   
    def test_connect_server_socket(self):
        self.game_server.server_socket = Mock()
        self.game_server.game_logger = Mock()
        self.game_server.connect_server_socket()
        self.game_server.server_socket.listen.assert_called_with(4)
        self.game_server.game_logger.log_info.assert_called_with("[CONNECTED] Game Server is online")

    def test_disconnect_server_socket(self):
        self.game_server.server_socket = Mock()
        self.game_server.game_logger = Mock()
        self.game_server.disconnect_server_socket()
        self.game_server.server_socket.close.assert_called_once()
        self.game_server.game_logger.log_info.assert_called_with(f"[DISCONNECTED] Game Server is offline")

    @patch("src.game_server.shuffle")
    def test_shuffle_positions(self,mock_shuffle):
        self.game_server.positions = [Positions.NORTH, Positions.EAST, Positions.WEST, Positions.SOUTH]
        self.game_server.shuffle_positions()
        mock_shuffle.assert_called_once_with(self.game_server.positions)


    @patch("time.sleep", return_value=None) 
    def test_broadcast_message(self,mock_sleep):
        self.mock_sockets = {
            "player1": Mock(),
            "player2": Mock(),
            "player3": Mock(),
            "player4": Mock()
        }
        self.game_server.player_sockets = self.mock_sockets
        message = "Hello Players"
        self.game_server.broadcast_message(message)
        for sock in self.mock_sockets.values():
            sock.sendall.assert_called_once_with((message + "\n").encode(ENCODER))
        self.assertEqual(mock_sleep.call_count, len(self.mock_sockets))


    def test_send_direct_message(self):
        player_socket = Mock()
        message = "Hello Player"
        self.game_server.send_direct_message(message,player_socket)
        player_socket.sendall.assert_called_once_with((message+"\n").encode(ENCODER))


    def test_accept_player_sockets(self):
        pass



    def test_assign_player(self):
        self.game_server.game_logger = Mock()
        player = "Tiago"
        self.game_server.assign_player(player)
        self.assertEqual(self.game_server.scores[player],0)    
        

    def tearDown(self):
        if self.game_server.server_socket:
            try:
                self.game_server.server_socket.close()
            except Exception:
                pass
        self.game_server.player_sockets = None
        self.game_server.players = None
        self.game_server.scores = None
        self.game_server = None



if __name__ == "__main__":
    unittest.main()
