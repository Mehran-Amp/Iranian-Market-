"""Persian/Arabic text normalization.

TSETMC data uses Arabic letters (U+064A, U+0643) and sometimes Arabic digits.
Users type Persian letters. Everything is normalized so both match.
"""
import re

# Display fix: only the letters that are wrong. Keeps ZWNJ and spacing as-is.
_FIX = str.maketrans({
    "\u064a": "\u06cc",  # Arabic Yeh -> Persian Yeh
    "\u0649": "\u06cc",  # Alef Maksura -> Persian Yeh
    "\u0643": "\u06a9",  # Arabic Kaf -> Persian Keheh
})

_SEARCH = {
    0x064A: "\u06cc",
    0x0649: "\u06cc",
    0x0643: "\u06a9",
    0x0629: "\u0647",  # Teh Marbuta -> Heh
    0x06C0: "\u0647",  # Heh with Yeh above -> Heh
    0x0640: None,      # Tatweel
    0x200C: " ",       # ZWNJ -> space
    0x200F: None,      # RTL mark
    0x200E: None,      # LTR mark
    0x0670: None,
}
for _cp in range(0x064B, 0x0653):  # Arabic diacritics
    _SEARCH[_cp] = None
for _i in range(10):
    _SEARCH[0x06F0 + _i] = str(_i)  # Persian digits
    _SEARCH[0x0660 + _i] = str(_i)  # Arabic-Indic digits

_WS = re.compile(r"\s+")


def fix_letters(text: str) -> str:
    """Return text with Arabic Yeh/Kaf replaced by Persian ones."""
    return text.translate(_FIX)


def normalize(text: str) -> str:
    """Canonical form used for search keys and ticker lookup."""
    text = text.translate(_SEARCH)
    return _WS.sub(" ", text).strip().lower()
