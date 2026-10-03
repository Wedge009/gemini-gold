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
count = 0
for section in ET.parse(game_cfg).getroot().find('colors').iter('section'):
    target = colors.setdefault(section.get('name'), {})
    for color in section.iter('color'):
        target[color.get('name')] = [float(color.get(c, 1)) for c in 'rgba']
        count += 1
with open(out_json, 'w') as f:
    json.dump(theme, f, indent=2)
    f.write('\n')
print(f'{count} colours written')
