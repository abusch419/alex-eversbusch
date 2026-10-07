"""Regenerate tables/*.json and pokeyellow.sym from a built pret/pokeyellow checkout.

Usage: python tools/gen_tables.py /path/to/pokeyellow
"""
import json
import re
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(__file__).resolve().parent.parent / "tables"
out.mkdir(exist_ok=True)


def quoted(path, macro):
    return re.findall(rf'^\s*{macro}\s+"([^"]*)"', (src / path).read_text(), re.M)


def consts(path, macro="const"):
    names = []
    for line in (src / path).read_text().splitlines():
        m = re.match(rf"\s*{macro}\s+(\w+)", line)
        if m:
            names.append(m.group(1))
        elif re.match(r"\s*const_skip", line):
            names.append(None)
    return names


# Species: internal index order (index 1 = RHYDON). names.asm is in internal order.
species_names = quoted("data/pokemon/names.asm", "dname")
dex_consts = re.findall(r"db\s+(DEX_\w+|0)", (src / "data/pokemon/dex_order.asm").read_text())
dex_ids = {n: i for i, n in enumerate(consts("constants/pokedex_constants.asm")) if n}
species = {}
for i, name in enumerate(species_names, start=1):
    d = dex_consts[i - 1]
    species[i] = {"name": name, "dex": dex_ids.get(d, 0)}

# Items: 1..N from names.asm, then HM01-05 ($C4) and TM01-50 ($C9).
items = {i: n for i, n in enumerate(quoted("data/items/names.asm", "li"), start=1)}
for k in range(5):
    items[0xC4 + k] = f"HM{k + 1:02d}"
for k in range(50):
    items[0xC9 + k] = f"TM{k + 1:02d}"

moves = {i: n for i, n in enumerate(quoted("data/moves/names.asm", "li"), start=1)}

maps = {}
for i, n in enumerate(consts("constants/map_constants.asm", "map_const")):
    if n:
        maps[i] = n.replace("_", " ").title()

charmap = {}
for m in re.finditer(r'charmap\s+"([^"]*)",\s*\$([0-9a-fA-F]+)', (src / "constants/charmap.asm").read_text()):
    val = int(m.group(2), 16)
    charmap.setdefault(val, m.group(1))

for name, data in [("species", species), ("items", items), ("moves", moves), ("maps", maps), ("charmap", charmap)]:
    (out / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
shutil.copy(src / "pokeyellow.sym", out / "pokeyellow.sym")
print({k: len(v) for k, v in [("species", species), ("items", items), ("moves", moves), ("maps", maps)]})
