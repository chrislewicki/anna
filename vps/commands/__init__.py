from typing import Dict, Callable, Awaitable
from .pint import ping
from .uptime import uptime
from .roll import roll
from .help import help_cmd

registry: Dict[str, Callable[..., Awaitable[str]]] = {
    "ping": ping,
    "uptime": uptime,
    "roll": roll,
    "help": help_cmd,
    "?": help_cmd,
}
