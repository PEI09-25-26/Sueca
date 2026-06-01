# Older Versions
    This folder contains all the different versions of the project that took place during development.  
    Each individual version of both frontend and backend served as new stepping stones in the development cycle, usually leading to or being caused by new implementations, refactoring or massive upgrades in existing systems.

# DISCLAIMER

    ALL these versions are deprecated, so some features might not work as intended or even break. These issues that may be present in this archive have been fixed in later versions of the project.

# In this Folder
## sueca_1.4_pubsub

    This version was the first one where we implemented a publish subscribe system, along with it being the version that preceeded the current version of the project (sueca_1.5). It ended up being the one with the biggest shift in implementation, as the swap from RESTAPI to a publish-subscribe system turned out to need more than just some simple adjustments, taking a while to complete. This version was also the version with the largest ammount of new features being planned, implemented and completed in. It also features the frontend of the application at the time, as well as better firebase implementations.

## Backend
### sueca_1.0

    This was the very first version where we implemented a simple local game of Sueca where 4 people could play in the terminal of a computer connected by websockets, simple as that.

### sueca_1.1

    This version saw the arrival of the very first artificial inteligence player with extremely simple logic, as well as better game logic and some small upgrades in the overall way the server views the players.

### sueca_1.2

    This version was the first big refactor in the way the game itself works, with the introduction of classes such as "card_mapper.py", "turn_displayer.py" and some slight reworks all around, the overall vision and system shifted into a Flask based environment (with some FastAPI presence too). The system now treated players seperately from the server itself better and the overall system ran in a more fluid way. Some files given to us by our project coordinator about an extremely early implementation idea for us to keep are also present in the "prof_files" folder.

### sueca_1.3

    This version saw the first attempt and development cycle around the implementation of the hybrid game mode, along with the implementation of different difficulty bots (random<weak<average<smart), the beggining of firebase implementation and other systems such as email verification and further advancements in the overall way the game is treated and handled, with the biggest winners of this version being the implementation of "game_state_tracker.py", "card_analyzer.py" and a rework on "card_mapper.py", which all helped us to get a deeper understanding of the game from a spectator's perspective during development and allowed the artificial inteligence players to have the proper information they needed for their decision making.

### sueca_1.4 (renamed to statistics-engine)

    This version is still in use in order to collect data from the agents, that being the main advancement that is present in this version, as the rest is also present in sueca_1.4_pubsub, along with the implementation of a publish-subscribe system. All of the work in this version was stopped and moved to sueca_1.4_pubsub later on, with the only thing worth mentioning being the statistic-analysis system which includes a completely automated and efficient way of running simulated matches with artificial inteligence players and extracting the maximum ammount of relevant information as possible. Every other part of this implementation was only kept as a way to keep development records, however, since it ended up remaining extremely useful even at the later stages of the project, it was ultimately decided it should be kept as its own stand-alone version.

## Frontend
### frontend_1.0

    The very first :D 

### frontend_REST

    This version

### frontend_pub_sub

    This version

## Computer Vision
### ComputerVision_1.0

    The version of the Computer Vision service that was used in this project's MVP and the very first completed model we used. It is structured around OpenCV and a bit of YOLO that work toguether to complete the full cycle of the card detection system needed for the physical and hybrid game-modes.

### ComputerVision_1.1

    This version is a straight up upgrade from the previous version, with the only couple of details worth mentioning seperately are the upgrades in the usage of the OpenCV model to cut the card into a rectangle and then using YOLO to detect and recognize the cut image.

### ComputerVision_1.2

    This is the final version used for the Computer Vision service in our project, it brings near to complete removal of the OpenCV model with a small ammount of exceptions where it is used, for a similar purpose than in the previous version. It also features an update on the version YOLO is running and a major upgrade on the overall system.

### DataSet_Creator

    These were the materials used when training our Computer Vision models. The info archived here ranges from the runs, the full dataset to other things such as the actual code implemented and the assets we used to train the models.
    