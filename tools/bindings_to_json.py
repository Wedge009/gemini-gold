#!/usr/bin/env python3
"""Convert the <bindings> section of a legacy vegastrike.config to bindings.json.

The game's own bindings come first. Actions from a reference bindings.json
(upstream Vega Strike's) are then added for commands the game doesn't bind,
as long as their key/button isn't already used, so newer engine commands such
as the settings screen still have a key.

Usage: bindings_to_json.py GAME_CONFIG REFERENCE_BINDINGS_JSON OUT_JSON
"""
import json
import sys
import xml.etree.ElementTree as ET


def modifier(value):
    # Old configs sometimes spell ctrl as "cntrl"; the engine only matches "ctrl".
    return (value or 'none').replace('cntrl', 'ctrl')


def convert(game_cfg):
    bindings = ET.parse(game_cfg).getroot().find('bindings')
    actions, axes = {}, {}
    for bind in bindings.iter('bind'):
        cmd = bind.get('command')
        entry = actions.setdefault(cmd, {})
        if bind.get('key') is not None:
            entry.setdefault('keyboard', []).append(
                {'key': bind.get('key'), 'modifier': modifier(bind.get('modifier'))})
        elif bind.get('mouse') is not None:
            entry.setdefault('mouse', []).append(
                {'button': int(bind.get('button')), 'modifier': modifier(bind.get('modifier'))})
        elif bind.get('joystick') is not None:
            entry.setdefault('joystick', []).append(
                {'joystick': int(bind.get('joystick')), 'button': int(bind.get('button')),
                 'modifier': modifier(bind.get('modifier'))})
    for axis in bindings.iter('axis'):
        name = axis.get('name')
        if name not in ('x', 'y', 'z', 'throttle'):
            continue
        source = 'mouse' if axis.get('mouse') is not None else 'joystick'
        # JSON holds one source per axis; the old config listed both mouse and
        # joystick for x/y. Keep the joystick, as upstream does; input.device
        # in config.json picks mouse flying at runtime.
        if name in axes and source == 'mouse':
            continue
        axes[name] = {'source': source,
                      'joystick': int(axis.get('joystick') or axis.get('mouse') or 0),
                      'axis': int(axis.get('axis')),
                      'inverse': axis.get('inverse', 'false').lower() == 'true'}
    return actions, axes


def used_inputs(actions):
    used = set()
    for entry in actions.values():
        for dev, lst in entry.items():
            for e in lst:
                used.add((dev, tuple(sorted(e.items()))))
    return used


def main(game_cfg, reference_json, out_json):
    actions, axes = convert(game_cfg)
    with open(reference_json) as f:
        reference = json.load(f)

    used = used_inputs(actions)
    added = []
    for cmd, entry in reference['actions'].items():
        if cmd in actions:
            continue
        kept = {dev: [e for e in lst if (dev, tuple(sorted(e.items()))) not in used]
                for dev, lst in entry.items()}
        kept = {dev: lst for dev, lst in kept.items() if lst}
        if kept:
            actions[cmd] = kept
            used |= used_inputs({cmd: kept})
            added.append(cmd)
    for name, axis in reference.get('axes', {}).items():
        axes.setdefault(name, axis)

    with open(out_json, 'w') as f:
        json.dump({'actions': actions, 'axes': axes}, f, indent=2)
        f.write('\n')
    print(f'{len(actions) - len(added)} game actions, {len(added)} added from reference: '
          + ', '.join(sorted(added)))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
