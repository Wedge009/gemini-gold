#!/usr/bin/env python3
"""Give each unit in units/units.csv the equipment listed in its Upgrades column.

Usage: tools/fold_upgrades.py [--write]

Gemini Gold gives ships their shields, reactor, radar, armour plating,
afterburner, ECM, repair droid and jump drive through the Upgrades column (for
example {shield_4_Level1;;}{reactor_level_0;;}). The current engine builds
ships from components and never applies that column, so ships came out with no
shields. This copies each listed item's stats from its <item>__upgrades row into
the unit's own row, in the fields the engine's components read:

- shields: shield, shield_facets, Shield_Recharge, Shield_Efficiency
- reactor: Reactor_Recharge, Primary_Capacitor
- radar: Can_Lock, Radar_Range, Tracking_Cone, Max_Cone, Lock_Cone
- afterburner: Afterburner_Usage_Cost
- ECM: ecm (from ECM_Rating), ECM_Resist, Ecm_Drain
- repair droid: repair (from Repair_Droid)
- jump drive: Jump_Drive_Present
- armour plating adds to the unit's eight Armor_* values; the total goes in
  armor_front/back/left/right, combined the way the engine combines the old
  eight facets into four.

The unit's own Armor_* and other base values are left alone, so running this
again gives the same result. .template rows (upgrade ceilings) and the upgrade
rows themselves are skipped, as are add_/mult_ items and items with no stats.
Run units/parser.py afterwards to regenerate units.json.
"""
import argparse
import csv
import re
from pathlib import Path

UNITS = Path(__file__).resolve().parent.parent / 'units'

NEW_COLUMNS = {
    'shield': 'shield=float (strength of each facet)',
    'shield_facets': 'int (2 or 4)',
    'armor_front': 'float', 'armor_back': 'float', 'armor_left': 'float', 'armor_right': 'float',
    'ecm': 'float', 'repair': 'float',
}
OLD_SHIELDS = ['Shield_Front_Top_Right', 'Shield_Back_Top_Left', 'Shield_Front_Bottom_Right', 'Shield_Front_Bottom_Left',
               'Shield_Back_Top_Right', 'Shield_Front_Top_Left', 'Shield_Back_Bottom_Right', 'Shield_Back_Bottom_Left']
# The engine's order for the old armour facets, and how it combines them into
# front, back, left and right (components/armor.cpp).
OLD_ARMOR = ['Armor_Front_Top_Left', 'Armor_Front_Top_Right', 'Armor_Front_Bottom_Left', 'Armor_Front_Bottom_Right',
             'Armor_Back_Top_Left', 'Armor_Back_Top_Right', 'Armor_Back_Bottom_Left', 'Armor_Back_Bottom_Right']
NEW_ARMOR = {'armor_front': (0, 1, 2, 3), 'armor_back': (4, 5, 6, 7), 'armor_left': (0, 2, 4, 6), 'armor_right': (1, 3, 5, 7)}
RADAR = ['Can_Lock', 'Radar_Range', 'Tracking_Cone', 'Max_Cone', 'Lock_Cone']


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt(value):
    return ('%.6f' % value).rstrip('0').rstrip('.')


def fold(unit, item, changes):
    """Apply one upgrade row's stats to a unit row (both dicts)."""
    shields = [number(item.get(k)) for k in OLD_SHIELDS]
    facets = [s for s in shields if s]
    armor = [number(item.get(k)) for k in OLD_ARMOR]
    applied = False
    if facets:
        changes['shield'] = fmt(max(facets))
        changes['shield_facets'] = '2' if len(facets) <= 2 else '4'
        for k in ('Shield_Recharge', 'Shield_Efficiency'):
            if item.get(k):
                changes[k] = item[k]
        applied = True
    if number(item.get('Reactor_Recharge')):
        for k in ('Reactor_Recharge', 'Primary_Capacitor'):
            if item.get(k):
                changes[k] = item[k]
        applied = True
    if number(item.get('Radar_Range')):
        for k in RADAR:
            if item.get(k):
                changes[k] = item[k]
        applied = True
    if number(item.get('Afterburner_Usage_Cost')):
        changes['Afterburner_Usage_Cost'] = item['Afterburner_Usage_Cost']
        applied = True
    if number(item.get('ECM_Rating')):
        changes['ecm'] = item['ECM_Rating']
        for k in ('ECM_Rating', 'ECM_Resist', 'Ecm_Drain'):
            if item.get(k):
                changes[k] = item[k]
        applied = True
    if number(item.get('Repair_Droid')):
        changes['repair'] = item['Repair_Droid']
        changes['Repair_Droid'] = item['Repair_Droid']
        applied = True
    if item.get('Jump_Drive_Present', '').upper() == 'TRUE':
        changes['Jump_Drive_Present'] = 'TRUE'
        applied = True
    if any(armor):
        changes.setdefault('_armor', [0.0] * 8)
        changes['_armor'] = [a + b for a, b in zip(changes['_armor'], armor)]
        applied = True
    return applied


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    path = UNITS / 'units.csv'
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header, types, data = rows[0], rows[1], rows[2:]
    for name, description in NEW_COLUMNS.items():
        if name not in header:
            header.append(name)
            types.append(description)
            for row in data:
                row.append('')
    col = {name: i for i, name in enumerate(header)}
    upgrades = {row[0]: dict(zip(header, row)) for row in data if row[0].endswith('__upgrades')}

    changed = 0
    for row in data:
        key = row[0]
        if key.endswith('__upgrades') or key.endswith('.template') or not row[col['Upgrades']]:
            continue
        unit = dict(zip(header, row))
        changes = {}
        used = []
        for name in re.findall(r'\{([^;}]*)', unit['Upgrades']):
            if name.startswith(('add_', 'mult_')):
                continue
            item = upgrades.get(name + '__upgrades')
            if item and fold(unit, item, changes):
                used.append(name)
        if '_armor' in changes:
            total = [number(unit.get(k)) + a for k, a in zip(OLD_ARMOR, changes.pop('_armor'))]
            for name, indices in NEW_ARMOR.items():
                changes[name] = fmt(sum(total[i] for i in indices) / 2)
        diff = {k: v for k, v in changes.items() if row[col[k]] != v}
        if diff:
            changed += 1
            print(f'{key} ({", ".join(used)}): ' + ', '.join(f'{k} {row[col[k]] or "-"} -> {v}' for k, v in diff.items()))
            for k, v in diff.items():
                row[col[k]] = v
    print(f'\n{changed} units changed')
    if args.write:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)
        print('Written; now run units/parser.py')
    else:
        print('Dry run; pass --write to change units.csv')


if __name__ == '__main__':
    main()
