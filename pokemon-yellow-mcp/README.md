# Pokémon Yellow MCP server

Runs Pokémon Yellow in PyBoy (in a window you can play) and lets Claude Desktop read live game state from RAM and press buttons.

## Setup (about 5 minutes)

1. Install [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. `cd pokemon-yellow-mcp && uv sync`
3. Test with your files:
   ```
   YELLOW_ROM=~/roms/yellow.gbc YELLOW_SAV=~/roms/yellow.sav uv run smoke_test.py
   ```
   It prints your party, money, badges and dex counts. A screenshot lands in `runtime/smoke.png`.
4. Add this to Claude Desktop's `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`), using absolute paths:
   ```json
   {
     "mcpServers": {
       "pokemon-yellow": {
         "command": "uv",
         "args": ["run", "--directory", "/ABSOLUTE/PATH/pokemon-yellow-mcp", "server.py"],
         "env": {
           "YELLOW_ROM": "/ABSOLUTE/PATH/yellow.gbc",
           "YELLOW_SAV": "/ABSOLUTE/PATH/yellow.sav"
         }
       }
     }
   }
   ```
   If Claude Desktop can't find `uv`, use its full path (`which uv`).
5. Restart Claude Desktop. The game window opens. Play with the keyboard (arrows, A=`a`, B=`s`, START=Enter, SELECT=Backspace) and ask Claude things like "where am I and what's my team?"

## Tools

| Tool | What it does |
|---|---|
| `get_game_state()` | Map + coords, battle flag, party (nickname, species, level, HP, moves/PP), money, coins, badges, dex seen/owned |
| `get_bag()` | Item names and counts |
| `get_battle()` | Enemy and our active mon; `{}` outside battle |
| `press_buttons(sequence, hold_frames=8)` | e.g. `["START"]`; returns new state |
| `screenshot()` | Current frame as PNG |
| `save_state(slot)` / `load_state(slot)` | Emulator states in `runtime/states/` |
| `read_memory(label_or_addr, length=1)` | Raw bytes by pret label (`wCurMap`) or hex (`D35D`) |

## Your save file

Your Delta `.sav` is never modified. It is copied to `runtime/working.sav` on first run, and in-game saves go there. To start over from the Delta file, delete `runtime/working.sav` (or set `YELLOW_SAV_RESET=1`). To move progress back to Delta, copy `runtime/working.sav` out.

## How addresses and names are resolved

`tables/pokeyellow.sym` comes from building [pret/pokeyellow](https://github.com/pret/pokeyellow) (the build matches the retail ROM SHA1). Species, item, move, map and text tables in `tables/*.json` are generated from the same source. Species are stored in internal index order (1 = Rhydon); each entry also carries its Pokédex number. To regenerate after a pret update: build pokeyellow, then `uv run tools/gen_tables.py /path/to/pokeyellow`.

## Notes

- The server only writes RAM through `load_state`. No cheats.
- Closing the game window ends the server; restart Claude Desktop to reopen it.
- `YELLOW_WINDOW=null` runs headless.
