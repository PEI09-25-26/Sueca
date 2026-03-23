from enum import Enum


class Positions(Enum):
    """This class represents a cardinal point.

    Maps each cardinal direction to a number. """
    NORTH = 1
    WEST = 2
    SOUTH = 3
    EAST = 4

    def __repr__(self):
        return self.name
