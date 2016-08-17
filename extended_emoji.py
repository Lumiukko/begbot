"""
This class extends the telegram.Emoji class by some additional unicode characters.
"""

from telegram import Emoji
from future.utils import bytes_to_native_str as n

# See: https://en.wikipedia.org/wiki/Regional_Indicator_Symbol
RIS = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲",
       "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]

ABC = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
       "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

ABC2RIS = dict(zip(ABC, RIS))


class ExtendedEmoji(Emoji):
    BOX_DRAWINGS_LIGHT_UP_AND_RIGHT = n(b"\xe2\x94\x94")
    BOX_DRAWINGS_LIGHT_VERTICAL_AND_RIGHT = n(b"\xe2\x94\x9c")
    BOX_DRAWINGS_LIGHT_VERTICAL = n(b"\xe2\x94\x82")

    @staticmethod
    def flag(cc):
        """
        Returns a countries flag emoji given its ISO 3166-1 alpha-2 country code.

        @param cc: ISO 3166-1 alpha-2 country code of the country.
        @return: UTF-8 encoded string of the countries flags emoji.
        """
        if len(cc) != 2:
            return "?"
        return "{}{}".format(ABC2RIS[cc[0]], ABC2RIS[cc[1]])
