from telegram import Emoji
from future.utils import bytes_to_native_str as n

RIS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲",
       "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]

ABC = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
       "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

ABC2RIS = dict(zip(ABC, RIS))

class ExtendedEmoji(Emoji):
    BOX_DRAWINGS_LIGHT_UP_AND_RIGHT = n(b"\xe2\x94\x94")
    BOX_DRAWINGS_LIGHT_VERTICAL_AND_RIGHT = n(b"\xe2\x94\x9c")

    def flag(cc):
        if len(cc) != 2:
            return "?"
        return "{}{}".format(ABC2RIS[cc[0]], ABC2RIS[cc[1]])