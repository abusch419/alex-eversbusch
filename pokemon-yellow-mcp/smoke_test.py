"""Boot the ROM headless, load the save, get past the title screen, print get_game_state()."""
import json
import os

os.environ.setdefault("YELLOW_SAV_RESET", "1")
from emulator import Emulator  # noqa: E402

emu = Emulator(window="null")
emu.pyboy.set_emulation_speed(0)

# Party RAM is only populated after CONTINUE. Mash START/A through intro, title, menu, and the save summary.
emu.tick(600)
for btn in ["start"] * 3 + ["a"] * 6:
    emu.pyboy.button_press(btn)
    emu.tick(10)
    emu.pyboy.button_release(btn)
    emu.tick(120)
emu.tick(300)

print(json.dumps(emu.ram.game_state(), indent=2, ensure_ascii=False))
emu.pyboy.screen.image.save("runtime/smoke.png")
emu.pyboy.stop(save=False)
