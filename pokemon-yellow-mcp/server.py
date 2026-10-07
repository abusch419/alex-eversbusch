"""MCP server exposing live Pokemon Yellow state from PyBoy over stdio."""
import os
import sys
import threading

import anyio
from mcp.server.fastmcp import FastMCP, Image

from emulator import Emulator

mcp = FastMCP("pokemon-yellow")
emu: Emulator = None  # set in main()


@mcp.tool()
def get_game_state() -> dict:
    """Current map and coordinates, battle flag, party (nickname, species, level, HP, moves/PP), money, coins, badges, Pokedex counts."""
    return emu.call(emu.ram.game_state)


@mcp.tool()
def get_bag() -> list[dict]:
    """Items in the bag with counts."""
    return emu.call(emu.ram.bag)


@mcp.tool()
def get_battle() -> dict:
    """Enemy species/level/HP and our active Pokemon. Empty object if not in battle."""
    return emu.call(emu.ram.battle)


@mcp.tool()
def press_buttons(sequence: list[str], hold_frames: int = 8) -> dict:
    """Press buttons in order, releasing between presses. Valid: A, B, START, SELECT, UP, DOWN, LEFT, RIGHT. Returns the new game state."""
    emu.press(sequence, hold_frames=max(1, hold_frames))
    return emu.call(emu.ram.game_state)


@mcp.tool()
def screenshot() -> Image:
    """Current frame as a PNG."""
    return Image(data=emu.screenshot_png(), format="png")


@mcp.tool()
def save_state(slot: str) -> str:
    """Save an emulator save state to disk under the given slot name."""
    return f"Saved to {emu.save_state(slot)}"


@mcp.tool()
def load_state(slot: str) -> str:
    """Load an emulator save state previously saved under the given slot name."""
    return f"Loaded {emu.load_state(slot)}"


@mcp.tool()
def read_memory(label_or_addr: str, length: int = 1) -> dict:
    """Debug: read raw bytes at a pret label (e.g. wCurMap) or hex address (e.g. D35D)."""
    return emu.call(lambda: emu.ram.raw(label_or_addr, max(1, min(length, 256))))


def _serve():
    try:
        anyio.run(mcp.run_stdio_async)
    finally:
        emu.running = False  # client disconnected: close the emulator


def main():
    global emu
    emu = Emulator(window=os.environ.get("YELLOW_WINDOW", "SDL2"))
    threading.Thread(target=_serve, daemon=True).start()
    emu.run_forever()  # SDL window must live on the main thread
    sys.exit(0)


if __name__ == "__main__":
    main()
