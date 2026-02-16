from typing import Dict, Callable, Awaitable
from .ping import ping
from .uptime import uptime
from .roll import roll
from .help import help_cmd
from .remind import remind
from .speedtest import speedtest
from .join import join
from .play import play
from .leave import leave
from .pause import pause
from .resume import resume
from .stop import stop
from .queue import queue
from .skip import skip
from .clear import clear
from .nowplaying import nowplaying

registry: Dict[str, Callable[..., Awaitable[str]]] = {
    "ping": ping,
    "uptime": uptime,
    "roll": roll,
    "help": help_cmd,
    "?": help_cmd,
    "remind": remind,
    "speedtest": speedtest,
    "join": join,
    "play": play,
    "leave": leave,
    "pause": pause,
    "resume": resume,
    "stop": stop,
    "queue": queue,
    "skip": skip,
    "clear": clear,
    "nowplaying": nowplaying,
    "np": nowplaying,
}
