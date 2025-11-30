import unittest
from src.player import *
from unittest.mock import Mock,patch,call
from src.constants import *
import builtins
class TestPlayer(unittest.TestCase):

    def setUp(self):
        self.player = Player("test_player")
        if hasattr(self.player, "player_socket") and self.player.player_socket:
            self.player.player_socket.close()
        self.player.player_socket = Mock()



    @patch("builtins.print")
    def test_connect_player_socket(self,mock_print):
        self.player.player_socket = Mock()
        self.player.connect_player_socket(server_ip="127.0.0.1")
        self.player.player_socket.connect.assert_called_once_with(("127.0.0.1",PORT))
        mock_print.assert_called_with(f"[CONNECTED] [NAME:{self.player.player_name}] [TO:127.0.0.1:{PORT}]")

    @patch("builtins.print")
    def test_disconnect_player_socket(self,mock_print):
        self.player.player_socket = Mock()
        self.player.running = True
        self.player.disconnect_player_socket()
        self.assertFalse(self.player.running)
        self.player.player_socket.close.assert_called_once()
        mock_print.assert_called_with(f"[DISCONNECTED] [{self.player.player_name}]")


    def test_send_card(self):
        self.player.player_socket = Mock()
        self.player.send_card(5)
        self.player.player_socket.send.assert_called_with(b"5")



    def test_send_repsonse(self):
        self.player.player_socket = Mock()
        self.player.send_response("top")
        self.player.player_socket.send.assert_called_with("top".encode(ENCODER))
        

    @patch("builtins.print")
    def test_receive_cards(self,mock_print):
        input_message = "[HAND]3 10 2 1 4 5 6 7 8 9"
        expected_hand = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.player.receive_cards(input_message)
        self.assertEqual(self.player.hand,expected_hand)
        mock_print.assert_called_with("[HAND-RECEIVED] Hand received")


    @patch("builtins.print")    
    @patch("builtins.input",side_effect=["-200"," ","25"])    
    @patch("src.player.Player.send_response")
    def test_handle_cut_deck_request(self,mock_send_response,mock_input,mock_print):

        self.player.handle_cut_deck_request()

        mock_send_response.assert_called_with("25")



    @patch("builtins.print")    
    @patch("builtins.input", side_effect=["top"])
    @patch("src.player.Player.send_response")
    def test_handle_trump_card_request_top(self, mock_send_response, mock_input, mock_print):
        self.player.handle_trump_card_request()

        mock_send_response.assert_called_once_with("top")



    @patch("builtins.print")    
    @patch("builtins.input", side_effect=["bottom"])
    @patch("src.player.Player.send_response")
    def test_handle_trump_card_request_bottom(self, mock_send_response, mock_input, mock_print):
        self.player.handle_trump_card_request()

        mock_send_response.assert_called_once_with("bottom")



    @patch("builtins.print")
    def tearDown(self,mock_print):
        if self.player:
            self.player.disconnect_player_socket()
        self.player = None


if __name__ == "__main__":
    unittest.main()