#!/usr/bin/env python3
"""Put the original Privateer's sector-map positions into universe/wcuniverse.xml.

Usage: tools/galaxy_positions.py EXTRACT_DIR [--write]

EXTRACT_DIR holds the decoded map CSVs described in tools/audit_map.py; this
reads rf_galaxy.csv (quadrant,quad_x,quad_y,system,sys_local_x,sys_local_y,...).
A system's sys_local_x/y are already sector-wide: the four quadrants share one
origin, where they meet.

Each Gemini system's xyz gets x and y from the original's position, at one
scale for both axes so the map keeps the original's proportions; the scale
and offsets are fitted to Gemini Gold's current positions, so the map stays the
same size and in the same place. z, the depth Gemini Gold gave each system (the
original's map is flat), is left as it is. Running this again changes nothing.
Without --write it only reports.
"""
import argparse
import csv
import re
from pathlib import Path

GAME_ROOT = Path(__file__).resolve().parent.parent


def key(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('extract_dir', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    with open(args.extract_dir / 'rf_galaxy.csv', newline='') as f:
        original = {key(r['system']): (int(r['sys_local_x']), int(r['sys_local_y'])) for r in csv.DictReader(f)}

    path = GAME_ROOT / 'universe/wcuniverse.xml'
    with open(path, newline='', encoding='utf-8') as f:
        text = f.read()
    gemini = re.search(r'<sector name="Gemini">.*?</sector>', text, re.S)
    systems = []  # (key, name, match of the xyz value)
    for m in re.finditer(r'<system name="([^"]+)">(.*?)</system>', gemini.group(0), re.S):
        xyz = re.search(r'(<var name="xyz" value=")([^"]*)(")', m.group(2))
        if xyz:
            systems.append((key(m.group(1)), m.group(1), gemini.start() + m.start(2) + xyz.start(2),
                            gemini.start() + m.start(2) + xyz.end(2), [float(v) for v in xyz.group(2).split()]))

    # Fit gg = s * original + offset, sharing s between the axes (least squares).
    pairs = [(xyz, original[k]) for k, _, _, _, xyz in systems if k in original]
    n = len(pairs)
    mx = sum(o[0] for _, o in pairs) / n; my = sum(o[1] for _, o in pairs) / n
    gx = sum(g[0] for g, _ in pairs) / n; gy = sum(g[1] for g, _ in pairs) / n
    num = sum((o[0] - mx) * (g[0] - gx) + (o[1] - my) * (g[1] - gy) for g, o in pairs)
    den = sum((o[0] - mx) ** 2 + (o[1] - my) ** 2 for _, o in pairs)
    s = num / den
    bx, by = gx - s * mx, gy - s * my
    print(f'Scale {s:.4f}, offset ({bx:.1f}, {by:.1f}) from {n} systems\n')

    new = text
    changed = 0
    for k, name, start, end, xyz in sorted(systems, key=lambda t: -t[2]):
        if k not in original:
            print(f'{name}: not in the original; left as is')
            continue
        ox, oy = original[k]
        x, y = round(s * ox + bx), round(s * oy + by)
        if abs(x - xyz[0]) <= 1 and abs(y - xyz[1]) <= 1:
            continue  # already there; re-fitting after rounding can shift a unit
        value = f'{x} {y} {xyz[2]:g}'
        changed += 1
        moved = ((x - xyz[0]) ** 2 + (y - xyz[1]) ** 2) ** 0.5
        print(f'{name}: ({xyz[0]:g}, {xyz[1]:g}) -> ({x}, {y}), moved {moved:.0f}')
        new = new[:start] + value + new[end:]
    print(f'\n{changed} systems moved')
    if args.write and new != text:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            f.write(new)
    elif not args.write:
        print('Dry run; pass --write to change universe/wcuniverse.xml')


if __name__ == '__main__':
    main()
