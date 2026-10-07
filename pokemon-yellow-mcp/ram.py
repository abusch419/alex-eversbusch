"""Symbol loading and RAM decoders for Pokemon Yellow (pret/pokeyellow labels)."""
import json
from pathlib import Path

TABLES = Path(__file__).parent / "tables"
BADGES = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"]
NUM_POKEMON = 151
NAME_LENGTH = 11
BATTLE_TYPES = {0: None, 1: "wild", 2: "trainer", 0xFF: "lost"}


def _load(name):
    return {int(k): v for k, v in json.loads((TABLES / f"{name}.json").read_text(encoding="utf-8")).items()}


SPECIES = _load("species")
ITEMS = _load("items")
MOVES = _load("moves")
MAPS = _load("maps")
CHARMAP = _load("charmap")


def load_symbols(path=TABLES / "pokeyellow.sym"):
    """Parse an rgbds .sym file into {label: address}. Only bank-0 WRAM/HRAM labels matter here."""
    syms = {}
    for line in Path(path).read_text().splitlines():
        line = line.split(";")[0].strip()
        if not line:
            continue
        loc, label = line.split()
        if ":" not in loc:
            continue  # constant, not an address
        bank, addr = loc.split(":")
        addr = int(addr, 16)
        if addr >= 0xC000:  # WRAM/HRAM (bank 00 for wram0, 01 for wramx in Yellow is unused)
            syms.setdefault(label, addr)
    return syms


SYM = load_symbols()


def species_name(i):
    return SPECIES.get(i, {}).get("name", f"#{i}")


def decode_text(data):
    out = []
    for b in data:
        if b in (0x50, 0x00):  # "@" terminator, or uninitialized RAM
            break
        ch = CHARMAP.get(b, "?")
        out.append(" " if ch == " " else ch)
    return "".join(out).strip()


def bcd(data):
    return int("".join(f"{b:02x}" for b in data))


def popcount(data, limit):
    bits = sum(bin(b).count("1") for b in data)
    if len(data) * 8 > limit:  # mask padding bits in the last byte
        last = data[-1] >> (limit - (len(data) - 1) * 8)
        bits -= bin(last).count("1")
    return bits


class RAM:
    """Reads decoded game state from any object supporting mem[addr] (PyBoy.memory)."""

    def __init__(self, mem):
        self.mem = mem

    def byte(self, label, off=0):
        return self.mem[SYM[label] + off]

    def read(self, addr, n):
        return bytes(self.mem[addr + i] for i in range(n))

    def bytes(self, label, n, off=0):
        return self.read(SYM[label] + off, n)

    def word(self, label, off=0):
        hi, lo = self.bytes(label, 2, off)
        return hi << 8 | lo

    def location(self):
        m = self.byte("wCurMap")
        return {"map_id": m, "map": MAPS.get(m, f"#{m}"), "x": self.byte("wXCoord"), "y": self.byte("wYCoord")}

    def _moves(self, moves_label, pp_label, off=0):
        out = []
        for i in range(4):
            mid = self.byte(moves_label, off + i)
            if mid:
                pp = self.byte(pp_label, off + i)
                out.append({"move": MOVES.get(mid, f"#{mid}"), "pp": pp & 0x3F, "pp_ups": pp >> 6})
        return out

    def party(self):
        count = min(self.byte("wPartyCount"), 6)
        size = SYM["wPartyMon2"] - SYM["wPartyMon1"]
        mons = []
        for i in range(count):
            off = i * size
            sid = self.byte("wPartyMon1Species", off)
            mons.append({
                "nickname": decode_text(self.bytes("wPartyMonNicks", NAME_LENGTH, i * NAME_LENGTH)),
                "species": species_name(sid),
                "level": self.byte("wPartyMon1Level", off),
                "hp": self.word("wPartyMon1HP", off),
                "max_hp": self.word("wPartyMon1MaxHP", off),
                "status": self.byte("wPartyMon1Status", off),
                "moves": self._moves("wPartyMon1Moves", "wPartyMon1PP", off),
            })
        return mons

    def bag(self):
        n = min(self.byte("wNumBagItems"), 20)
        out = []
        for i in range(n):
            iid, qty = self.bytes("wBagItems", 2, i * 2)
            if iid == 0xFF:
                break
            out.append({"item": ITEMS.get(iid, f"#{iid}"), "count": qty})
        return out

    def in_battle(self):
        return BATTLE_TYPES.get(self.byte("wIsInBattle"), "unknown")

    def battle(self):
        kind = self.in_battle()
        if kind not in ("wild", "trainer"):
            return {}

        def mon(p):
            return {
                "species": species_name(self.byte(f"{p}Species")),
                "level": self.byte(f"{p}Level"),
                "hp": self.word(f"{p}HP"),
                "max_hp": self.word(f"{p}MaxHP"),
                "status": self.byte(f"{p}Status"),
            }

        enemy = mon("wEnemyMon")
        ours = mon("wBattleMon")
        ours["nickname"] = decode_text(self.bytes("wBattleMonNick", NAME_LENGTH))
        ours["moves"] = self._moves("wBattleMonMoves", "wBattleMonPP")
        return {"type": kind, "enemy": enemy, "active": ours}

    def game_state(self):
        badges = self.byte("wObtainedBadges")
        dex_len = (NUM_POKEMON + 7) // 8
        return {
            "player": decode_text(self.bytes("wPlayerName", NAME_LENGTH)),
            "location": self.location(),
            "in_battle": self.in_battle(),
            "party": self.party(),
            "money": bcd(self.bytes("wPlayerMoney", 3)),
            "coins": bcd(self.bytes("wPlayerCoins", 2)),
            "badges": [b for i, b in enumerate(BADGES) if badges >> i & 1],
            "dex_seen": popcount(self.bytes("wPokedexSeen", dex_len), NUM_POKEMON),
            "dex_owned": popcount(self.bytes("wPokedexOwned", dex_len), NUM_POKEMON),
        }

    def raw(self, label_or_addr, length=1):
        s = label_or_addr.strip()
        if s in SYM:
            addr = SYM[s]
        else:
            addr = int(s.lstrip("$").removeprefix("0x"), 16)
        data = self.read(addr, length)
        return {"addr": f"0x{addr:04X}", "hex": data.hex(" "), "bytes": list(data)}
