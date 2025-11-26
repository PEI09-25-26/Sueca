from game_logger import GameLogger
def main():

    def do_this():
        logger = GameLogger()
        logger.log_debug("Boogie woogie")
        logger.log_error("WATCH OUT!!")
        logger.log_warning("THIS IS A WARNING!")


    do_this()

    pile = [
                "♣|2", "♣|3", "♣|4", "♣|5", "♣|6", "♣|Q", "♣|J", "♣|K", "♣|7", "♣|A",
                "♦|2", "♦|3", "♦|4", "♦|5", "♦|6", "♦|Q", "♦|J", "♦|K", "♦|7", "♦|A",
                "♥|2", "♥|3", "♥|4", "♥|5", "♥|6", "♥|Q", "♥|J", "♥|K", "♥|7", "♥|A",
                "♠|2", "♠|3", "♠|4", "♠|5", "♠|6", "♠|Q", "♠|J", "♠|K", "♠|7", "♠|A"
            ]

    
main()

