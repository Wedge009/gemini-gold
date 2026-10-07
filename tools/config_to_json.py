#!/usr/bin/env python3
"""Carry game-specific settings from a legacy vegastrike.config into config.json.

The current engine no longer reads vegastrike.config. This script:
  1. diffs the game's vegastrike.config against a base one (upstream Vega Strike's)
     so only the settings the game actually changed are considered;
  2. maps each changed <var> onto a JSON key the engine reads, using the key list
     scraped from the engine's configuration.cpp;
  3. writes those values over a starting config.json, and reports anything it
     could not place.

Usage:
  config_to_json.py BASE_CONFIG GAME_CONFIG ENGINE_CONFIGURATION_CPP \
                    START_CONFIG_JSON OUT_CONFIG_JSON REPORT_TXT
"""
import json
import re
import sys
import xml.etree.ElementTree as ET

# Old XML section path -> new JSON prefix, where the name changed.
SECTION_MAP = {
    'ai': 'ai',
    'ai/firing': 'ai.firing',
    'ai/targetting': 'ai.targeting',
    'cockpitaudio': 'cockpit_audio',
    'unitaudio': 'audio',
    'hud': 'graphics.hud',
    'graphics/mesh': 'graphics.mesh',
    'graphics/general': 'graphics',
}

# Old (section/name) -> new JSON path, where the key itself was renamed.
# None means "don't carry over": a by-name match that would land on the wrong
# setting (graphics/vdu_static is an animation, cockpit_audio.vdu_static a sound).
KEY_MAP = {
    'graphics/x_resolution': 'graphics.resolution_x',
    'graphics/y_resolution': 'graphics.resolution_y',
    'graphics/vdu_static': None,
    'AI/Firing/MaximumFiringAngle.minagg': 'ai.firing.maximum_firing_angle.minagg',
    'AI/Firing/MaximumFiringAngle.maxagg': 'ai.firing.maximum_firing_angle.maxagg',
    'physics/autotime': 'physics.auto_time_in_seconds',
    'physics/indestructable_cargo_items': 'physics.indestructible_cargo_items',
    'physics/insystem_jump_or_timeless_auto-pilot': 'physics.in_system_jump_or_timeless_auto_pilot',
    'physics/planet_port_min_size': 'dock.planet_dock_port_min_size',
    'physics/planet_port_size': 'dock.planet_dock_port_size',
    'physics/player_autoeject': 'physics.ejection.player_auto_eject',
    'physics/refire_difficutly_scaling': 'physics.refire_difficulty_scaling',
    'physics/special_and_normal_gun_combo': 'physics.allow_special_and_normal_gun_combo',
    'audio/threadtime': 'audio.thread_time',
    'graphics/base_alpha_test_cutoff': 'graphics.bases.alpha_test_cutoff',
    'graphics/base_print_cargo_volume': 'graphics.bases.print_cargo_volume',
    'graphics/hud/MaxMissileDiamondSize': 'graphics.hud.max_missile_bracket_size',
    'graphics/hud/MinMissileDiamondSize': 'graphics.hud.min_missile_bracket_size',
    'graphics/hud/basename:basename': 'graphics.hud.basename_colon_basename',
    'graphics/insys_jump_animation': 'graphics.in_system_jump_animation',
    'graphics/insys_jump_animation_size': 'graphics.in_system_jump_animation_size',
    'graphics/jumpgate': 'graphics.jump_gate',
    'graphics/jumpgatesize': 'graphics.jump_gate_size',
    'graphics/star_alpha_test_cutoff': 'graphics.stars_alpha_test_cutoff',
    'graphics/tractor.scoop': 'physics.tractor.scoop',
    'unitaudio/jumparrive': 'audio.unit_audio.jump_arrive',
    'unitaudio/jumpleave': 'audio.unit_audio.jump_leave',
    'cockpitaudio/missle_switch': 'cockpit_audio.missile_switch',
}


def flatten(path):
    root = ET.parse(path).getroot()
    out = {}

    def walk(elem, prefix):
        for child in elem:
            if child.tag == 'section':
                walk(child, prefix + [child.get('name')])
            elif child.tag == 'var':
                out['/'.join(prefix + [child.get('name')])] = child.get('value')

    for variables in root.iter('variables'):
        walk(variables, [])
    return out


def engine_paths(cpp_path):
    """Return {json.path: type} for every key configuration.cpp reads."""
    pattern = re.compile(r'^\s+([a-z_]+(?:\.[a-z_0-9]+)+) = boost::json::value_to<([a-z:]+)>')
    paths = {}
    with open(cpp_path) as f:
        for line in f:
            m = pattern.match(line)
            if m:
                path = re.sub(r'_(dbl|flt)$', '', m.group(1))
                paths.setdefault(path, m.group(2))
    return paths


def convert(value, kind):
    v = value.strip()
    if kind == 'bool':
        if v.lower() in ('true', '1', 'yes', 'on'):
            return True
        if v.lower() in ('false', '0', 'no', 'off', ''):
            return False
        raise ValueError(value)
    if kind in ('int', 'unsigned', 'size_t', 'uint32_t'):
        return int(float(v))
    if kind in ('double', 'float'):
        return float(v)
    return value


def snake(name):
    """AllowCivilWar -> allow_civil_war, tractor.scoop -> tractor_scoop."""
    name = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', name)
    return name.replace('.', '_').replace('-', '_').lower()


def resolve(old_key, paths):
    """Return (json_path, how) or (None, candidates)."""
    if old_key in KEY_MAP:
        if KEY_MAP[old_key] is None:
            return None, []
        return KEY_MAP[old_key], 'renamed'
    section, _, raw_name = old_key.rpartition('/')
    section = section.lower()
    prefix = SECTION_MAP.get(section, section.replace('/', '.'))
    names = [raw_name.lower()]
    if snake(raw_name) not in names:
        names.append(snake(raw_name))
    for name in names:
        direct = f'{prefix}.{name}' if prefix else name
        if direct in paths:
            return direct, 'direct' if name == names[0] else 'snake_case'
    candidates = []
    for name in names:
        leaf_matches = [p for p in paths if p.rsplit('.', 1)[-1] == name]
        # Prefer a match under the old section, e.g. audio.unit_audio.shield
        # rather than cockpit_audio.shield for unitaudio/shield.
        in_section = [p for p in leaf_matches if p.startswith(prefix + '.')]
        if len(in_section) == 1:
            return in_section[0], 'by-name'
        if len(leaf_matches) == 1:
            return leaf_matches[0], 'by-name'
        candidates += leaf_matches
    return None, candidates


def set_path(tree, path, value):
    *parents, leaf = path.split('.')
    for p in parents:
        tree = tree.setdefault(p, {})
    tree[leaf] = value


def main(base_cfg, game_cfg, cpp, start_json, out_json, report_txt):
    base, game = flatten(base_cfg), flatten(game_cfg)
    paths = engine_paths(cpp)
    with open(start_json) as f:
        config = json.load(f)

    applied, unmapped, ambiguous, bad = [], [], [], []
    for key in sorted(game):
        if base.get(key) == game[key]:
            continue
        path, how = resolve(key, paths)
        if path is None:
            (ambiguous if how else unmapped).append((key, game[key], how))
            continue
        try:
            value = convert(game[key], paths.get(path, 'string'))
        except ValueError:
            bad.append((key, game[key], path))
            continue
        set_path(config, path, value)
        applied.append((key, path, how, value))

    with open(out_json, 'w') as f:
        json.dump(config, f, indent=4)
        f.write('\n')

    with open(report_txt, 'w') as f:
        f.write(f'Applied {len(applied)} settings\n')
        for key, path, how, value in applied:
            f.write(f'  {key} -> {path} = {value!r} ({how})\n')
        f.write(f'\nAmbiguous ({len(ambiguous)}): more than one engine key with this name\n')
        for key, value, cands in ambiguous:
            f.write(f'  {key} = {value!r}: {", ".join(cands)}\n')
        f.write(f'\nBad values ({len(bad)})\n')
        for key, value, path in bad:
            f.write(f'  {key} = {value!r} (wanted for {path})\n')
        f.write(f'\nNot read by the engine any more ({len(unmapped)})\n')
        for key, value, _ in unmapped:
            f.write(f'  {key} = {value!r}\n')
    print(f'applied {len(applied)}, ambiguous {len(ambiguous)}, '
          f'bad {len(bad)}, unmapped {len(unmapped)}')


if __name__ == '__main__':
    if len(sys.argv) != 7:
        sys.exit(__doc__)
    main(*sys.argv[1:])
