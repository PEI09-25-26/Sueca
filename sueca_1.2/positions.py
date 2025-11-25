from enum import Enum

class Positions(Enum):
    NORTH = 1
    WEST = 2
    SOUTH = 3
    EAST = 4

    def __repr__(self):
        return self.name
