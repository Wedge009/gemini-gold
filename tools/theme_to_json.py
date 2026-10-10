#!/usr/bin/env python3
"""Overlay the <colors> section of a legacy vegastrike.config onto a theme.json.

Usage: theme_to_json.py GAME_CONFIG START_THEME_JSON OUT_THEME_JSON
"""
import json
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 4:
    sys.exit(__doc__)
game_cfg, start_json, out_json = sys.argv[1:]

with open(start_json) as f:
    theme = json.load(f)
colors = theme.setdefault('colors', {})
# A colour either gives r, g, b and a, or refers to another colour (ref="red", optionally
# in another section="..."), which is resolved once every colour is read.
count = 0
xml = {}
for section in ET.parse(game_cfg).getroot().find('colors').iter('section'):
    for color in section.iter('color'):
        xml[(section.get('name'), color.get('name'))] = color


def resolve(key, seen=()):
    color = xml[key]
    ref = color.get('ref')
    if ref is None:
        return [float(color.get(c, 1)) for c in 'rgba']
    target = (color.get('section', key[0]), ref)
    if target in seen or target not in xml:
        sys.exit(f'{key[0]}/{key[1]}: cannot resolve ref {target[0]}/{target[1]}')
    return resolve(target, seen + (key,))


for (section, name) in xml:
    colors.setdefault(section, {})[name] = resolve((section, name))
    count += 1
with open(out_json, 'w') as f:
    json.dump(theme, f, indent=2)
    f.write('\n')
print(f'{count} colours written')
