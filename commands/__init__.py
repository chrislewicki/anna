from typing import Dict, Callable, Awaitable
from .ping import ping
from .uptime import uptime
from .roll import roll
from .help import help_cmd
from .remind import remind
from .reminders import reminders
from .cancel import cancel
from .speedtest import speedtest
from .join import join
from .play import play
from .playnext import playnext
from .leave import leave
from .pause import pause
from .resume import resume
from .stop import stop
from .queue import queue
from .skip import skip
from .clear import clear
from .nowplaying import nowplaying
from .shuffle import shuffle
from .remove import remove
from .move import move
from .loop import loop
from .volume import volume
from .autoplay import autoplay
from .saved_playlists import saveq, loadq, playlists, delq
from .choose import choose
from .eightball import eightball

registry: Dict[str, Callable[..., Awaitable[str]]] = {
    "ping": ping,
    "uptime": uptime,
    "roll": roll,
    "help": help_cmd,
    "?": help_cmd,
    "remind": remind,
    "reminders": reminders,
    "cancel": cancel,
    "speedtest": speedtest,
    "join": join,
    "play": play,
    "playnext": playnext,
    "leave": leave,
    "pause": pause,
    "resume": resume,
    "stop": stop,
    "queue": queue,
    "skip": skip,
    "clear": clear,
    "nowplaying": nowplaying,
    "np": nowplaying,
    "shuffle": shuffle,
    "remove": remove,
    "move": move,
    "loop": loop,
    "volume": volume,
    "autoplay": autoplay,
    "saveq": saveq,
    "loadq": loadq,
    "playlists": playlists,
    "delq": delq,
    "choose": choose,
    "8ball": eightball,
}
