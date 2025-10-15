from game import *

def main():
    game = Game(["Pedro","Tiago","Lucas","Gonçalo"])
    i = 0
    while i<10:
        print(f"This game's trump is {game.get_trump_card()}")
        game._round()
        i+=1      
    game._show_final_scores_and_print_winner()
       
main() 