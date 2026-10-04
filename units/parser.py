# Convert units.csv (plus units_description.csv) to units.json, the file the engine reads.
#
# units.csv's first row names the columns and its second row describes their types;
# every row after that is a unit. Each unit becomes a JSON object keyed by the
# column names, leaving out empty cells. The engine reads every value as a string.

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    # Row 0 is the header, row 1 the type descriptions.
    return rows[0], rows[2:]


def main():
    headers, rows = read_rows(HERE / 'units.csv')
    units = []
    for row in rows:
        if not any(row):
            continue
        if len(row) != len(headers):
            raise SystemExit(f'{row[0]}: {len(row)} columns, expected {len(headers)}')
        units.append({h: v for h, v in zip(headers, row) if v != ''})

    # units_description.csv overrides Textual_Description, matching keys case-insensitively.
    # Descriptions for keys not in units.csv become description-only entries, as before.
    by_key = {}
    for unit in units:
        by_key.setdefault(unit['Key'].lower(), []).append(unit)
    _, descriptions = read_rows(HERE / 'units_description.csv')
    for row in descriptions:
        if len(row) < 2 or not row[0]:
            continue
        key, text = row[0], row[1]
        matches = by_key.get(key.lower())
        if matches:
            for unit in matches:
                unit['Textual_Description'] = text
        else:
            units.append({'Key': key, 'Textual_Description': text})

    with open(HERE / 'units.json', 'w', encoding='utf-8') as f:
        json.dump(units, f, indent=4, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(units)} units to units.json')


if __name__ == '__main__':
    main()
