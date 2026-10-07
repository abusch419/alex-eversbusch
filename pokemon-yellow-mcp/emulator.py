"""PyBoy wrapper. The emulator runs on the main thread (SDL needs it); other threads submit jobs."""
import os
import queue
import shutil
import threading
from concurrent.futures import Future
from pathlib import Path

from pyboy import PyBoy

from ram import RAM

HERE = Path(__file__).parent
RUNTIME = HERE / "runtime"
STATES = RUNTIME / "states"
BUTTONS = {"A": "a", "B": "b", "START": "start", "SELECT": "select",
           "UP": "up", "DOWN": "down", "LEFT": "left", "RIGHT": "right"}


def require_env(name):
    val = os.environ.get(name)
    if not val or not Path(val).expanduser().is_file():
        raise SystemExit(f"{name} must point to an existing file (got {val!r})")
    return Path(val).expanduser()


class Emulator:
    def __init__(self, window="SDL2"):
        rom = require_env("YELLOW_ROM")
        RUNTIME.mkdir(exist_ok=True)
        STATES.mkdir(exist_ok=True)
        ram_kwargs = {}
        sav = os.environ.get("YELLOW_SAV")
        if sav:
            sav = require_env("YELLOW_SAV")
            # Work on a copy so the Delta export is never modified.
            work = RUNTIME / "working.sav"
            if not work.exists() or os.environ.get("YELLOW_SAV_RESET") == "1":
                shutil.copy(sav, work)
            self._ram_file = open(work, "r+b")
            ram_kwargs["ram_file"] = self._ram_file
        self.pyboy = PyBoy(str(rom), window=window, sound_emulated=False, **ram_kwargs)
        self.pyboy.set_emulation_speed(1)
        self.ram = RAM(self.pyboy.memory)
        self.frame = 0
        self._jobs = queue.Queue()
        self._frame_cv = threading.Condition()
        self.running = True

    # --- main thread ---
    def run_forever(self):
        while self.running:
            self._drain_jobs()
            if not self.pyboy.tick():
                break
            with self._frame_cv:
                self.frame += 1
                self._frame_cv.notify_all()
        self.running = False
        with self._frame_cv:
            self._frame_cv.notify_all()
        self._drain_jobs()
        self.pyboy.stop()

    def _drain_jobs(self):
        while True:
            try:
                fn, fut = self._jobs.get_nowait()
            except queue.Empty:
                return
            try:
                fut.set_result(fn())
            except BaseException as e:
                fut.set_exception(e)

    def tick(self, n):
        """Headless helper for scripts that own the loop."""
        for _ in range(n):
            self.pyboy.tick()
            self.frame += 1

    # --- any thread ---
    def call(self, fn, timeout=10):
        """Run fn on the emulator thread between frames (acts as the lock)."""
        if threading.current_thread() is threading.main_thread():
            return fn()
        fut = Future()
        self._jobs.put((fn, fut))
        return fut.result(timeout)

    def wait_frames(self, n):
        with self._frame_cv:
            target = self.frame + n
            while self.running and self.frame < target:
                self._frame_cv.wait(1)

    def press(self, sequence, hold_frames=8, gap_frames=8):
        names = [s.strip().upper() for s in sequence]
        bad = [s for s in names if s not in BUTTONS]
        if bad:
            raise ValueError(f"Unknown buttons {bad}; valid: {list(BUTTONS)}")
        for s in names:
            self.call(lambda: self.pyboy.button_press(BUTTONS[s]))
            self.wait_frames(hold_frames)
            self.call(lambda: self.pyboy.button_release(BUTTONS[s]))
            self.wait_frames(gap_frames)

    def screenshot_png(self):
        import io
        img = self.call(lambda: self.pyboy.screen.image.copy())
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    @staticmethod
    def _slot_path(slot):
        safe = "".join(c for c in slot if c.isalnum() or c in "-_") or "default"
        return STATES / f"{safe}.state"

    def save_state(self, slot):
        path = self._slot_path(slot)

        def job():
            with open(path, "wb") as f:
                self.pyboy.save_state(f)
        self.call(job)
        return str(path)

    def load_state(self, slot):
        path = self._slot_path(slot)
        if not path.exists():
            raise FileNotFoundError(f"No save state named {slot!r}")

        def job():
            with open(path, "rb") as f:
                self.pyboy.load_state(f)
        self.call(job)
        return str(path)
