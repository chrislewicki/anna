# Anna

Anna is a self-hosted Discord bot for music, reminders, and small server utilities.
She plays audio from YouTube and resolves links from every major streaming service,
keeps per-server queues and saved playlists, and runs happily in a single Docker
container on a VPS.

## Talking to Anna

Every command is a mention: `@Anna <command> [args]`. Replying to one of Anna's
messages works too. Saying "anna" in passing (without a mention) just earns you a 👀.

```
@Anna help          list all commands
@Anna help play     detailed usage for one command
```

## Music

Anna joins your voice channel automatically when you ask her to play something
(or use `@Anna join` / `@Anna leave` explicitly). She leaves on her own after
5 minutes of silence or an empty channel.

### Playing things

| Command | What it does |
|---|---|
| `@Anna play <query>` | Play a URL or search YouTube for the words |
| `@Anna play <playlist url>` | Queue an entire playlist, in order |
| `@Anna play` | Restart a stopped queue |
| `@Anna playnext <query>` | Queue a track ahead of everything else |

`play` accepts a lot of input shapes:

- **YouTube / YouTube Music** video and playlist links
- **Spotify, Apple Music, Tidal, Deezer, Amazon Music, SoundCloud, Pandora**
  single-track links — resolved to YouTube via [odesli](https://odesli.co)
- **Spotify and Apple Music playlists and albums** — every track queued in
  order, including user-created Apple Music playlists (no API keys required)
- **Plain search terms** — first YouTube result wins

Playlist tracks are resolved lazily at playback time, so queueing a
100-track playlist is instant.

### Controlling playback

| Command | What it does |
|---|---|
| `@Anna pause` / `@Anna resume` | Pause and resume the current track |
| `@Anna skip` | Skip to the next track (works even in `loop track` mode) |
| `@Anna stop` | Stop playback and halt the queue — `@Anna play` picks it back up |
| `@Anna volume [0-200]` | Show or set volume; applies to the current track immediately |
| `@Anna nowplaying` (`np`) | Current track with playback progress |

### Managing the queue

| Command | What it does |
|---|---|
| `@Anna queue` | Show what's playing and what's next |
| `@Anna shuffle` | Shuffle the queued tracks |
| `@Anna remove <n>` | Remove the track at position n |
| `@Anna move <from> <to>` | Reorder the queue |
| `@Anna clear` | Wipe the queue |
| `@Anna loop [track\|queue\|off]` | Repeat the current track, cycle the whole queue, or play through once |
| `@Anna autoplay [on\|off]` | When the queue runs dry, keep playing related tracks (YouTube mix radio) |

If a track can't be played (region-locked, deleted, no search results), Anna
says so in the channel and moves on instead of going quiet.

### Saved playlists

Snapshot the current queue under a name and bring it back any time. Saved
playlists are per-server and survive restarts.

| Command | What it does |
|---|---|
| `@Anna saveq <name>` | Save the playing track + queue as a named playlist |
| `@Anna loadq <name>` | Queue up a saved playlist |
| `@Anna playlists` | List this server's saved playlists |
| `@Anna delq <name>` | Delete one |

## Reminders

| Command | What it does |
|---|---|
| `@Anna remind <time> <message>` | Set a reminder for yourself |
| `@Anna remind @user <time> <message>` | Set one for someone else |
| `@Anna reminders` | List your pending reminders |
| `@Anna cancel <n\|all>` | Cancel one (by number from the list) or all |

Time formats: `30s`, `5m`, `2h`, `1d`, combined like `1h30m`, or clock times
like `at 17:30` / `at 5pm` (next occurrence; interpreted in `REMINDER_TIMEZONE`
from `config.py`). Reminders persist to disk and survive restarts; Anna pings
you in the channel where you set them.

## Fun & utilities

| Command | What it does |
|---|---|
| `@Anna roll <dice>` | RPG dice: `d20`, `2d6`, `3d8+5`, `5x d20` |
| `@Anna choose a \| b \| c` | Pick one at random (also splits on commas or spaces) |
| `@Anna 8ball <question>` | The magic 8-ball knows all |
| `@Anna ping` | pong |
| `@Anna uptime` | How long the bot has been running |
| `@Anna speedtest` | Network speed test from the host (takes ~30s) |

## Running Anna

Anna runs as a single Docker container. She needs a Discord bot token with the
message content, voice, and guild intents enabled. Put it in a `.env` file next
to `docker-compose.yml`:

```
DISCORD_TOKEN=your-token
```

then:

```bash
docker compose up -d --build
```

Or without Docker (requires Python 3.11+, ffmpeg, and libopus):

```bash
pip install -r requirements.txt
DISCORD_TOKEN=your-token python bot.py
```

### Configuration

Tunables live in `config.py`:

- `ANNA_ROLE_IDS` — role mentions that also trigger the bot
- `REMINDER_TIMEZONE` — IANA timezone for `at 5pm`-style reminders (default UTC)
- `IDLE_DISCONNECT_SECONDS` — voice idle timeout (default 300)
- `REMINDER_MIN_TIME_SECONDS` / `REMINDER_MAX_TIME_SECONDS` — reminder bounds

### Persistence

Two JSON files hold state across restarts (both mounted as volumes in
`docker-compose.yml` so they outlive the container):

- `reminders.json` — pending reminders
- `playlists.json` — saved playlists

## Development

The code is organized as one module per concern, with one file per command:

```
bot.py               entry point, Discord client, background tasks
message_handler.py   mention parsing → command dispatch
command_router.py    command extraction and routing
commands/            one handler per command (auto-listed by help)
music_manager.py     voice connections, queues, playback, loop/autoplay/volume
playlist_resolver.py streaming-service playlist links → track lists
streaming_resolver.py single streaming links → YouTube (via odesli)
playlist_store.py    saved playlists (JSON persistence)
reminder_manager.py  reminder storage and scheduling
```

Tests are offline and deterministic (network and Discord are faked):

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```
