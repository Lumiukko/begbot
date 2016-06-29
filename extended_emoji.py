from telegram import Emoji
from future.utils import bytes_to_native_str as n

class ExtendedEmoji(Emoji):
    BOX_DRAWINGS_LIGHT_UP_AND_RIGHT = n(b"\xe2\x94\x94")
    BOX_DRAWINGS_LIGHT_VERTICAL_AND_RIGHT = n(b"\xe2\x94\x9c")
