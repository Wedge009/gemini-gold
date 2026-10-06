#!/usr/bin/env python3
"""Put the original Privateer's in-system positions into sectors/Gemini.

Usage: tools/map_positions.py EXTRACT_DIR [--scale K] [--flip-z] [--write]

EXTRACT_DIR holds the decoded map CSVs described in tools/audit_map.py. Righteous
Fire's layout is used: it matches base Privateer's everywhere both have an
object, adds Eden, and redesigns Blockade Point Alpha, whose Righteous Fire
story mission needs the new nav points. Gemini Gold is one continuous game
covering both, so the map is Righteous Fire's throughout.

Every jump point, base, nav marker and asteroid field is moved to K times its
original (x, y, z). Nav points and asteroid fields (including those at hidden
points) that the original has and Gemini Gold left out are added. Objects with no original counterpart (Eden's
moon, the Tr'Pakh weapon dump) keep their offset from the nearest base or
asteroid field. Gemini Gold's current scale is fitted from the jumps and bases, so
running this again changes nothing. Without --write it only reports.
"""
import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path

GAME_ROOT = Path(__file__).resolve().parent.parent

TAG = re.compile(r'<(planet|unit|asteroid)\b([^>]*)>', re.I)
ATTR = re.compile(r'(\w+)(\s*=\s*)"([^"]*)"')
FIELD = ('        <unit difficulty=".03" name=""  file="Asteroid_Field" faction="neutral"   '
         'x="{x}" y="{y}" z="{z}" day="-14000"  ></unit>\n')
NAV_MARKER = ('        <planet name="Nav_{n}" file="invisible.png" alpha="ONE ONE" radius="256" gravity="0" '
              'x="{x}" y="{y}" z="{z}" day="240" />\n')


def key(name):
    name = name.lower()
    if name.startswith('jump_to_'):
        name = name[len('jump_to_'):]
    return re.sub(r'[^a-z0-9]', '', name)


def load_points(extract_dir, game, flip_z=False):
    points = defaultdict(list)
    with open(extract_dir / f'{game}_navpoints.csv', newline='') as f:
        for row in csv.DictReader(f):
            row['pos'] = (int(row['x']), int(row['y']), -int(row['z']) if flip_z else int(row['z']))
            points[key(row['system'])].append(row)
    return points


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt(v):
    return str(int(round(v)))


class Tag:
    def __init__(self, m, branch):
        self.start, self.end = m.span(2)
        self.kind = m.group(1).lower()
        self.attrs = {a.group(1): a.group(3) for a in ATTR.finditer(m.group(2))}
        self.text = m.group(2)
        self.branch = branch
        self.pos = (number(self.attrs.get('x')), number(self.attrs.get('y')), number(self.attrs.get('z')))
        f = self.attrs.get('file', '')
        if 'destination' in self.attrs:
            self.role = 'jump'
        elif f.startswith('stars/'):
            self.role = 'star'
        elif 'Asteroid_Field' in f or 'AField' in f:
            self.role = 'field'
        elif 'invisible' in f:
            self.role = 'nav'
        else:
            self.role = 'base'
        self.target = None

    def rewrite(self):
        x, y, z = (fmt(v) for v in self.target)
        text = self.text
        previous = None
        for name, value in (('x', x), ('y', y), ('z', z)):
            pattern = re.compile(r'(\b%s\s*=\s*)"[^"]*"' % name)
            if pattern.search(text):
                text = pattern.sub(lambda m: m.group(1) + '"%s"' % value, text, count=1)
            elif previous:
                # A missing coordinate goes straight after the one before it.
                text = re.sub(r'(\b%s\s*=\s*"[^"]*")' % previous, lambda m: m.group(1) + ' %s="%s"' % (name, value), text, count=1)
            else:
                text = ' x="%s"' % value + text
            previous = name
        return text


def parse(text):
    comments = [m.span() for m in re.finditer(r'<!--.*?-->', text, re.S)]
    tags = []
    branches = []
    for m in re.finditer(r'<Condition\s+expression="([^"]*)"|</Condition>|' + TAG.pattern, text, re.I):
        if any(a <= m.start() < b for a, b in comments):
            continue
        if m.group(0).startswith('<Condition'):
            branches.append(m.group(1))
        elif m.group(0).startswith('</Condition'):
            if branches:
                branches.pop()
        else:
            tm = TAG.match(text, m.start())
            tags.append(Tag(tm, branches[-1] if branches else None))
    return tags


def fit(pairs):
    """Gemini Gold's current scale on one axis: the median of gg / original.

    The median rather than a least-squares fit, so a few objects still at other
    positions (such as a system being changed to another layout) don't shift it.
    """
    ratios = sorted(g / o for g, o in pairs if abs(o) >= 1000)
    return ratios[len(ratios) // 2] if ratios else 1.0


def plan_system(name, text, original, scale, report):
    tags = parse(text)
    jumps = {key(r['ref_name']): r for r in original if r['kind'] == 'jump'}
    bases = {key(r['ref_name']): r for r in original if r['kind'] == 'base'}
    by_index = {i + 1: r for i, r in enumerate(original)}

    def counterpart(t):
        if t.role == 'jump':
            return jumps.get(key(t.attrs['destination'].split('/')[-1]))
        if t.role == 'base':
            if t.attrs.get('name'):
                return bases.get(key(t.attrs['name']))
            left = [b for b in bases if not any(key(o.attrs.get('name', '')) == b for o in tags if o.role == 'base')]
            return bases[left[0]] if len(left) == 1 else None
        if t.role == 'nav':
            m = re.fullmatch(r'Nav[_ ](\d+)', t.attrs.get('name', ''))
            r = m and by_index.get(int(m.group(1)))
            return r if r and r['kind'] == 'nav' else None
        return None

    pairs = []
    for t in tags:
        r = counterpart(t)
        if r is not None:
            t.target = tuple(scale * v for v in r['pos'])
            t.orig = r
            if t.role in ('jump', 'base'):
                pairs.append((t.pos, r['pos']))
    return tags, pairs


def place_rest(name, tags, original, scale, kx, ky, report):
    """Asteroid fields and objects with no original counterpart."""
    def estimate(pos):
        return (pos[0] / kx, pos[1] / ky)

    named = {}
    for t in tags:
        if t.target is not None and t.attrs.get('name'):
            named[key(t.attrs['name'])] = t.orig
        if t.target is not None and t.role == 'base' and not t.attrs.get('name'):
            named['__pirate__'] = t.orig
            pirate_pos = t.pos
    fields = [r for r in original if r['asteroid_field'].strip()]
    claimed = set()
    for t in tags:
        if t.role != 'field':
            continue
        n = key(t.attrs.get('name', ''))
        r = named.get(n)
        if r is None and not n and '__pirate__' in named and t.pos[:2] == pirate_pos[:2]:
            r = named['__pirate__']
        if r is None:
            # A free-standing field: the nearest original field, matched in the plane.
            ex = estimate(t.pos)
            candidates = sorted(fields, key=lambda f: math.dist(ex, f['pos'][:2]))
            r = candidates[0] if candidates else None
            if r is not None and math.dist(ex, r['pos'][:2]) > 20000:
                report.append(f'field at ({t.pos[0]:g}, {t.pos[1]:g}) has no original field nearby; left as is')
                r = None
        if r is not None:
            t.target = tuple(scale * v for v in r['pos'])
            claimed.add(id(r))
    # Moons and the like belong to a planet or base, or sit in an asteroid field.
    anchors = [t for t in tags if t.target is not None and t.role in ('base', 'field')]
    for t in tags:
        if t.target is not None or t.role in ('star', 'field'):
            continue
        if not anchors:
            report.append(f'{t.attrs.get("name")} has nothing to keep its position relative to')
            continue
        ex = estimate(t.pos)
        a = min(anchors, key=lambda o: math.dist(ex, estimate(o.pos)))
        ax, ay = estimate(a.pos)
        t.target = (a.target[0] + scale * (ex[0] - ax), a.target[1] + scale * (ex[1] - ay),
                    a.target[2] + scale * (t.pos[2] - a.pos[2]) / ((kx + ky) / 2))
        report.append(f'{t.attrs.get("name") or t.attrs.get("file")} kept beside {a.attrs.get("name") or "an asteroid field"}')
    missing = [r for r in fields if id(r) not in claimed]
    return missing


def add_fields(text, tags, missing, scale):
    """Add an asteroid field for each original field the file lacks.

    One Asteroid_Field unit per field, after the existing ones: the engine
    ignores <Condition> blocks, so the system files no longer have detail
    variants of each field.
    """
    fields = ''.join(FIELD.format(**dict(zip('xyz', (fmt(scale * v) for v in r['pos'])))) for r in missing)
    existing = [t for t in tags if t.role == 'field']
    at = text.index('\n', existing[-1].end) + 1 if existing else text.rindex('</system>')
    return text[:at] + fields + text[at:]


def add_navs(text, tags, original, scale):
    """Add a marker for each regular nav point the original has and the file lacks.

    Markers are named Nav_<n>, n being the point's place in the original's list,
    as Gemini Gold names its existing ones. Returns the text and the points added.
    """
    have = {int(m.group(1)) for t in tags if t.role == 'nav'
            for m in [re.fullmatch(r'Nav[_ ](\d+)', t.attrs.get('name', ''))] if m}
    added = [(i + 1, r) for i, r in enumerate(original) if r['kind'] == 'nav' and i + 1 not in have]
    if not added:
        return text, []
    markers = ''.join(NAV_MARKER.format(n=n, **dict(zip('xyz', (fmt(scale * v) for v in r['pos']))))
                      for n, r in added)
    # After the last nav marker or jump point, so the objects stay grouped.
    anchors = [t for t in tags if t.role in ('nav', 'jump') and not t.branch]
    at = text.index('\n', anchors[-1].end) + 1 if anchors else text.rindex('</system>')
    return text[:at] + markers + text[at:], added


def newline_of(text):
    return '\r\n' if text.count('\r\n') * 2 > text.count('\n') else '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('extract_dir', type=Path)
    parser.add_argument('--scale', type=float, default=0.29)
    parser.add_argument('--flip-z', action='store_true', help="negate the original's z (if systems turn out mirrored)")
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    rf = load_points(args.extract_dir, 'rf', args.flip_z)
    priv = load_points(args.extract_dir, 'priv', args.flip_z)
    files = sorted((GAME_ROOT / 'sectors/Gemini').glob('*.system'))

    planned = []
    all_pairs = []
    for path in files:
        k = key(path.stem)
        original = rf.get(k) or priv.get(k)
        if not original:
            print(f'{path.stem}: not in the original; skipped')
            continue
        with open(path, errors='replace', newline='') as f:
            text = f.read()
        report = []
        tags, pairs = plan_system(path.stem, text, original, args.scale, report)
        planned.append((path, text, original, tags, report))
        all_pairs += pairs
    kx = fit([(g[0], o[0]) for g, o in all_pairs])
    ky = fit([(g[1], o[1]) for g, o in all_pairs])
    print(f'Current scale: x {kx:.3f}, y {ky:.3f}; new scale {args.scale} on all three axes\n')

    for path, text, original, tags, report in planned:
        missing = place_rest(path.stem, tags, original, args.scale, kx, ky, report)
        moved = [t for t in tags if t.target is not None and any(abs(a - b) >= 1 for a, b in zip(t.target, t.pos))]
        unplaced = [t for t in tags if t.target is None and t.role != 'star']
        new = text
        for t in sorted((t for t in tags if t.target is not None), key=lambda t: -t.start):
            new = new[:t.start] + t.rewrite() + new[t.end:]
        plain = new.replace('\r\n', '\n')
        plain, navs = add_navs(plain, parse(plain), original, args.scale)
        if navs:
            report.append('added ' + ', '.join(f'Nav_{n} at {r["pos"]}' for n, r in navs))
        if missing:
            plain = add_fields(plain, parse(plain), missing, args.scale)
            report.append(f'added {len(missing)} asteroid field(s) at ' +
                          ', '.join(f'{r["kind"]} {r["pos"]}' for r in missing))
        if navs or missing:
            new = plain.replace('\n', newline_of(text))
        for t in unplaced:
            report.append(f'{t.role} {t.attrs.get("name")!r} not matched; left as is')
        if moved or missing or navs or report:
            print(f'{path.stem}: {len(moved)} moved')
            for line in report:
                print('  -', line)
        if args.write and new != text:
            with open(path, 'w', newline='') as f:
                f.write(new)
    if not args.write:
        print('\nDry run; pass --write to change the system files.')


if __name__ == '__main__':
    main()
