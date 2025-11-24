from enum import Enum

class Positions(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    def __repr__(self):
        return self.name


