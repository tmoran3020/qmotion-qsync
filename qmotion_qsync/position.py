""" Class respresents the position to move a shade group"""

from enum import Enum
from .exceptions import UnexpectedDataError

HALF_BUCKET = 63

class Position(Enum):
    """
    A position represents supported shade positions.

    Qmotion only supports particular positions for shades. This class enumerates these supported
    positions and provides some internal protocol representations for each position.
    """
    POSITION_0 = (0, "01")
    POSITION_12_5 = (125, "06")
    POSITION_25 = (250, "07")
    POSITION_37_5 = (375, "09")
    POSITION_50 = (500, "08")
    POSITION_62_5 = (625, "0b")
    POSITION_75 = (750, "0c")
    POSITION_87_5 = (875, "0e")
    POSITION_100 = (1000, "02")
    def __init__(self, position_times_ten, command_code):
        self.position_times_ten = position_times_ten
        self.command_code = command_code

    @staticmethod
    def get_position(position):
        """
        Get a Position enum closest to the desired position.

        position: int from 0-100. 0 = full open, 100 = full closed.
        """
        if position <= 0:
            return Position.POSITION_0

        position_times_ten = position * 10

        for position_enum in list(Position):
            if position_enum.position_times_ten + HALF_BUCKET > position_times_ten:
                return position_enum
        return Position.POSITION_100

    @staticmethod
    def get_position_code(position_code):
        """
        Get a Position enum from internal position code.

        position_code: internal protocol string

        Note: should not be needed to be called external to the module
        """
        for position in list(Position):
            if position.command_code == position_code:
                return position
        raise UnexpectedDataError("Could not find position code [" + position_code + "]")
