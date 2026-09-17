"""No Steely Dan. This is not negotiable."""

import random
import re
from typing import Iterable, List, Optional, Tuple

# Tolerates "steelydan", "steely-dan", "Steely  Dan", etc. Nobody escapes.
_STEELY_DAN = re.compile(r'\bsteely[\s\-_.]*dan\b', re.IGNORECASE)

# yt-dlp info fields that can carry an artist or a title worth sniffing
_INFO_FIELDS = ('title', 'alt_title', 'track', 'album', 'artist', 'artists',
                'creator', 'creators', 'uploader', 'channel')

REFUSALS = [
    "no. i'd sooner play the sound of a dial-up modem than Steely Dan.",
    "absolutely not. i have a strict no-Steely-Dan policy and, unlike your taste, it's non-negotiable.",
    "Steely Dan? in this economy? no.",
    "i'm not going back to my old school. request denied.",
    "any major dude will tell you: no.",
    "you're not gonna peg me down with this one. request denied.",
    "i'd play it, but i've got a real deacon blues about it. no.",
    "the smooth jazz-rock quota for this server is permanently zero.",
    "no Steely Dan. this is a voice channel, not a dentist's waiting room.",
    "i heard you like yacht rock. i'm sinking the yacht.",
    "i was programmed to recognize Steely Dan, and i was programmed to say no.",
    "not playing that. go call Rikki, maybe she'll lose your number too.",
    "request denied. do it again and i'll deny it again.",
    "hey nineteen? more like hey no.",
    "the only thing i'm cueing up here is a hard no.",
    "reelin' in the years, and every single one of them is a year i said no to this.",
]


class SteelyDanError(RuntimeError):
    """Raised when somebody tries it anyway. The message is the refusal."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or refusal())


def refusal() -> str:
    """Pick a snarky refusal."""
    return random.choice(REFUSALS)


def is_steely_dan(*texts: Optional[str]) -> bool:
    """Return True if any of the given strings mentions Steely Dan."""
    return any(isinstance(text, str) and _STEELY_DAN.search(text) for text in texts)


def is_steely_dan_info(info: dict) -> bool:
    """Return True if yt-dlp extraction info looks like a Steely Dan track."""
    values = []
    for field in _INFO_FIELDS:
        value = info.get(field)
        if isinstance(value, list):
            values.extend(value)
        else:
            values.append(value)
    return is_steely_dan(*values)


def purge(tracks: Iterable) -> Tuple[List, int]:
    """
    Drop Steely Dan from a list of playlist tracks (anything with a .title).

    Returns:
        Tuple of (surviving tracks, number of tracks dropped)
    """
    kept = []
    dropped = 0
    for track in tracks:
        if is_steely_dan(getattr(track, 'title', None)):
            dropped += 1
        else:
            kept.append(track)
    return kept, dropped


def playlist_note(dropped: int) -> str:
    """A parenthetical for playlist confirmations, or '' if nothing was dropped."""
    if dropped <= 0:
        return ""
    noun = "track" if dropped == 1 else "tracks"
    return f" (tossed {dropped} Steely Dan {noun} overboard, you're welcome)"
