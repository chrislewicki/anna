from typing import Dict, Callable, Awaitable
from .ping import ping
from .uptime import uptime
from .roll import roll
from .help import help_cmd
from .remind import remind
from .speedtest import speedtest

registry: Dict[str, Callable[..., Awaitable[str]]] = {
    "ping": ping,
    "uptime": uptime,
    "roll": roll,
    "help": help_cmd,
    "?": help_cmd,
    "remind": remind,
    "speedtest": speedtest,
}
