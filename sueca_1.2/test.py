from deck import *
def main():
    d = Deck()
    print(d)
    print("Shuffling")
    d.shuffle_deck()
    print(d)

    print("Cutting")
    d.cut_deck(2)
    print(d)

    
main()