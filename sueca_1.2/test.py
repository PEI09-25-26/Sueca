from game_logger import GameLogger
def main():

    def do_this():
        logger = GameLogger()
        logger.log_debug("Boogie woogie")
        logger.log_error("WATCH OUT!!")
        logger.log_warning("THIS IS A WARNING!")


    do_this()

    
main()