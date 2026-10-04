#!/usr/bin/env python3
"""Compare Gemini Gold's map with the original Privateer's.

Usage: tools/audit_map.py EXTRACT_DIR [--game priv|rf]

EXTRACT_DIR holds CSVs decoded from the original game's SECTORS.IFF (one set
per game, prefixed priv_ or rf_; the default is rf, Righteous Fire):
  <game>_navpoints.csv  system,kind,x,y,z,icon_radius,trigger_radius,ref_name,asteroid_field
                        kind is jump, base, nav or hidden_trigger; ref_name is the
                        jump destination or base name; asteroid_field is empty for none
  <game>_galaxy.csv     quadrant,quad_x,quad_y,system,sys_local_x,sys_local_y,...

For every system in sectors/Gemini this reports jumps, bases, nav points and
asteroid fields that differ, jump lists in universe/wcuniverse.xml that disagree
with the system file, and objects whose position doesn't fit the overall
scale between the two maps (Gemini Gold drops the original's z axis).
"""
import argparse
import csv
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

GAME_ROOT = Path(__file__).resolve().parent.parent
# Objects further than this from where the overall scale puts them are reported
# (in original game units; nav points are typically 20000-60000 from the centre).
POSITION_TOLERANCE = 15000


def key(name):
    """Match names across the two games: 'Jump_To_Pender's_Star' -> 'pendersstar'."""
    name = name.lower()
    if name.startswith('jump_to_'):
        name = name[len('jump_to_'):]
    return re.sub(r'[^a-z0-9]', '', name)


def load_original(extract_dir, game):
    points = defaultdict(list)
    with open(extract_dir / f'{game}_navpoints.csv', newline='') as f:
        for row in csv.DictReader(f):
            points[key(row['system'])].append(row)
    with open(extract_dir / f'{game}_galaxy.csv', newline='') as f:
        names = {key(row['system']): row['system'] for row in csv.DictReader(f)}
    return points, names


def load_universe():
    root = ET.parse(GAME_ROOT / 'universe/wcuniverse.xml').getroot()
    gemini = next(s for s in root.iter('sector') if s.get('name') == 'Gemini')
    systems = {}
    for system in gemini.findall('system'):
        values = {v.get('name'): v.get('value') or '' for v in system.findall('var')}
        systems[key(system.get('name'))] = values
    return systems


def load_system_file(path):
    """Return (kind, attributes) for each object, keeping the high-detail asteroid fields."""
    text = re.sub(r'<!--.*?-->', '', path.read_text(errors='replace'), flags=re.S)
    objects = []
    conditions = []
    for m in re.finditer(r'<Condition\s+expression="([^"]*)"|</Condition>|<(planet|unit|asteroid)\b([^>]*)>', text, re.I):
        if m.group(1) is not None:
            conditions.append(m.group(1))
            continue
        if m.group(2) is None:
            if conditions:
                conditions.pop()
            continue
        attrs = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', m.group(3)))
        file = attrs.get('file', '')
        if 'destination' in attrs:
            kind = 'jump'
        elif file.startswith('stars/'):
            continue
        elif 'Asteroid_Field' in file or 'AField' in file:
            # Each field is listed twice, once per asteroid_detail level; keep one.
            if conditions and '&lt;' in conditions[-1]:
                continue
            kind = 'asteroid'
        elif 'invisible' in file:
            kind = 'nav'
        else:
            kind = 'base'
        objects.append((kind, attrs))
    return objects


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def audit_system(name, original, objects, universe, report, positions):
    o_jumps = {key(r['ref_name']): r for r in original if r['kind'] == 'jump'}
    o_bases = {key(r['ref_name']): r for r in original if r['kind'] == 'base'}
    o_navs = [r for r in original if r['kind'] == 'nav']
    o_hidden = [r for r in original if r['kind'] == 'hidden_trigger']

    g_jumps = {key(a['destination'].split('/')[-1]): a for k, a in objects if k == 'jump'}
    g_bases = {key(a['name']): a for k, a in objects if k == 'base' and a.get('name')}
    g_navs = [a for k, a in objects if k == 'nav']
    # Pirate bases are unnamed in Gemini Gold; pair one with the only unmatched original base.
    for k, a in objects:
        if k == 'base' and not a.get('name'):
            unmatched = [b for b in o_bases if b not in g_bases]
            if len(unmatched) == 1:
                g_bases[unmatched[0]] = a
            else:
                report.append(f'unnamed base ({a.get("file")}) not matched')

    for d in sorted(set(o_jumps) - set(g_jumps)):
        report.append(f'jump to {o_jumps[d]["ref_name"]} missing')
    for d in sorted(set(g_jumps) - set(o_jumps)):
        report.append(f'extra jump to {g_jumps[d]["destination"]}')
    for b in sorted(set(o_bases) - set(g_bases)):
        report.append(f'base {o_bases[b]["ref_name"]} missing')
    for b in sorted(set(g_bases) - set(o_bases)):
        report.append(f'extra base "{g_bases[b].get("name")}" ({g_bases[b].get("file")})')

    if universe is None:
        report.append('missing from universe/wcuniverse.xml')
    else:
        jumps = {key(j.split('/')[-1]) for j in universe.get('jumps', '').split()}
        full = {key(j.split('/')[-1]) for j in universe.get('fulljumps', '').split()} - {'gemini'}
        if set(g_jumps) not in (jumps, full):
            report.append(f'wcuniverse.xml jumps {sorted(jumps)} differ from the system file {sorted(g_jumps)}')

    if len(g_navs) != len(o_navs) or o_hidden:
        report.append(f'nav points: {len(g_navs)} here; original has {len(o_navs)} plus {len(o_hidden)} hidden')

    # Asteroid fields: named after the object they surround, or after a nav point, or unnamed.
    def free(n):
        return not n or re.fullmatch(r'nav\d*|asteroidfield|asteroid', key(n))
    g_fields = [a for k, a in objects if k == 'asteroid']
    g_named = {key(a['name']) for a in g_fields if not free(a.get('name'))}
    g_free = sum(1 for a in g_fields if free(a.get('name')))
    o_fields = [r for r in original if r['asteroid_field'].strip()]
    o_named = {key(r['ref_name']) for r in o_fields if r['ref_name']}
    o_free = [r for r in o_fields if not r['ref_name']]
    # A pirate base's field is unnamed here because the base is.
    for b, a in g_bases.items():
        if not a.get('name') and b in o_named:
            o_named.discard(b)
            o_free.append(o_bases[b])
    for n in sorted(o_named - g_named):
        report.append(f'asteroid field at {n} missing')
    for n in sorted(g_named - o_named):
        report.append(f'extra asteroid field at {n}')
    if g_free != len(o_free):
        hidden = sum(1 for r in o_free if r['kind'] == 'hidden_trigger')
        report.append(f'free-standing asteroid fields: {g_free} here; original has {len(o_free)} ({hidden} at hidden points)')

    for found, wanted in ((g_jumps, o_jumps), (g_bases, o_bases)):
        for k, a in found.items():
            if k in wanted:
                r = wanted[k]
                positions.append((name, a.get('name') or r['ref_name'], number(a.get('x')), number(a.get('y')),
                                  int(r['x']), int(r['y'])))


def scale(pairs):
    """Least-squares scale through the origin for gg = k * original."""
    den = sum(o * o for _, o in pairs)
    return sum(g * o for g, o in pairs) / den if den else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('extract_dir', type=Path)
    parser.add_argument('--game', choices=('priv', 'rf'), default='rf')
    args = parser.parse_args()

    points, names = load_original(args.extract_dir, args.game)
    universe = load_universe()
    files = {key(p.stem): p for p in (GAME_ROOT / 'sectors/Gemini').glob('*.system')}
    reports = {}
    positions = []

    for k in sorted(set(names) | set(files)):
        name = names.get(k, files[k].stem if k in files else k)
        report = []
        if k not in names:
            report.append('not in the original')
        elif k not in files:
            report.append('no system file')
        else:
            audit_system(name, points[k], load_system_file(files[k]), universe.get(k), report, positions)
        if report:
            reports[name] = report

    kx = scale([(p[2], p[4]) for p in positions])
    ky = scale([(p[3], p[5]) for p in positions])
    for system, obj, gx, gy, ox, oy in positions:
        off = math.hypot(gx / kx - ox, gy / ky - oy)
        if off > POSITION_TOLERANCE:
            reports.setdefault(system, []).append(
                f'{obj} at ({gx:g}, {gy:g}) is {off:.0f} from where the scale puts the original ({ox}, {oy})')

    print(f'Scale: x = {kx:.3f} * original x, y = {ky:.3f} * original y ({len(positions)} jumps and bases)\n')
    for system in sorted(reports):
        print(system)
        for line in reports[system]:
            print('  -', line)


if __name__ == '__main__':
    main()
