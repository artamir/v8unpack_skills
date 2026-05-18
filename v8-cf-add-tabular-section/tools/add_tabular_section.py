"""Add a tabular section (ТабличнаяЧасть) to a catalog in a v8unpack source directory.

The tabular section definition is read from a reference catalog directory and
inserted into the target catalog's Catalog.json.

Usage:
    python add_tabular_section.py <source_dir> <catalog_name> <ts_name> <ts_source_catalog_dir>

Arguments:
    source_dir              Path to the v8unpack source directory to modify.
    catalog_name            Name of the catalog folder (e.g. "Справочник01").
    ts_name                 Name of the tabular section to add (e.g. "ТабличнаяЧасть1").
    ts_source_catalog_dir   Directory containing the source Catalog.json.

The tool modifies source_dir/Catalog/<catalog_name>/Catalog.json in-place:
  - Appends the TS entry to header[0][5]
  - Increments the TS count at header[0][5][1]
Also writes Catalog.tabular_sections.json with human-readable properties.
"""
import argparse
import json
import os
import sys

CATALOG_JSON = 'Catalog.json'
CATALOG_TABULAR_SECTIONS_JSON = 'Catalog.tabular_sections.json'

# Path inside Catalog.json that holds the tabular sections list.
# Format: ["<type_uuid>", "<count>", ts_entry1, ts_entry2, ...]
TS_LIST_PATH = ['header', 0, 5]


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def _get_ts_list(catalog_data):
    """Navigate to and return the tabular sections list within a Catalog.json structure."""
    obj = catalog_data
    for key in TS_LIST_PATH:
        obj = obj[key]
    return obj  # ["type_uuid", "count", ts_entry1, ts_entry2, ...]


# ---------------------------------------------------------------------------
# TS accessors
# ---------------------------------------------------------------------------

def _ts_name(ts_entry):
    """Extract TS name from a tabular section entry."""
    return ts_entry[0][1][5][1][2].strip('"')


def _ts_uuid(ts_entry):
    """Extract TS UUID from a tabular section entry."""
    return ts_entry[0][1][5][1][1][2]


# ---------------------------------------------------------------------------
# Column accessors (columns have same internal structure as attributes)
# ---------------------------------------------------------------------------

def _col_name(col_entry):
    """Extract column name from a column entry."""
    return col_entry[0][1][1][1][2].strip('"')


def _col_uuid(col_entry):
    """Extract column UUID from a column entry."""
    return col_entry[0][1][1][1][1][2]


# ---------------------------------------------------------------------------
# Property parsing helpers
# ---------------------------------------------------------------------------

def _parse_synonym(raw):
    """Parse synonym raw list to {lang: text} dict.

    Format: [count, '"lang1"', '"text1"', '"lang2"', '"text2"', ...]
    """
    if not isinstance(raw, list) or len(raw) < 3:
        return {}
    result = {}
    i = 1
    while i + 1 < len(raw):
        lang = raw[i].strip('"')
        text = raw[i + 1].strip('"')
        if lang:
            result[lang] = text
        i += 2
    return result


def _parse_type(type_pattern):
    """Parse type_pattern list to a human-readable dict."""
    if not isinstance(type_pattern, list) or len(type_pattern) < 2:
        return {}
    details = type_pattern[1]
    if not isinstance(details, list) or not details:
        return {}
    kind = details[0].strip('"')
    if kind == 'S':
        return {'kind': 'String', 'length': int(details[1]) if len(details) > 1 else 0}
    if kind == 'N':
        return {
            'kind': 'Number',
            'digits': int(details[1]) if len(details) > 1 else 0,
            'precision': int(details[2]) if len(details) > 2 else 0,
        }
    if kind == 'B':
        return {'kind': 'Boolean'}
    if kind == 'D':
        return {'kind': 'Date', 'parts': details[1].strip('"') if len(details) > 1 else ''}
    if kind == '#':
        return {'kind': 'Ref', 'type_uuid': details[1] if len(details) > 1 else ''}
    return {'kind': kind}


def _unwrap_tag(val):
    """Extract tag string from ['"TAG"'] list or return str(val)."""
    if isinstance(val, list) and val:
        return val[0].strip('"')
    return str(val)


def _col_props(col_entry):
    """Parse raw column entry to a human-readable properties dict."""
    meta = col_entry[0][1][1][1]
    uuid = meta[1][2]
    synonym = _parse_synonym(meta[3])
    type_props = _parse_type(col_entry[0][1][1][2])
    pb = col_entry[0][1]
    return {
        'uuid': uuid,
        'synonym': synonym,
        'type': type_props,
        'indexing': str(pb[7]) if len(pb) > 7 else '0',
        'use': _unwrap_tag(pb[8]) if len(pb) > 8 else 'U',
        'fill_check': _unwrap_tag(pb[9]) if len(pb) > 9 else 'U',
    }


def _ts_props(ts_entry):
    """Parse raw TS entry to a human-readable properties dict (without columns)."""
    meta = ts_entry[0][1][5][1]  # ['3', uuid_holder, '"name"', synonym, '"comment"', ...]
    uuid = _ts_uuid(ts_entry)
    synonym = _parse_synonym(meta[3]) if len(meta) > 3 else {}
    comment = meta[4].strip('"') if len(meta) > 4 else ''
    return {
        'uuid': uuid,
        'synonym': synonym,
        'comment': comment,
    }


def _rebuild_tabular_sections_json(catalog_dir, ts_list):
    """Write Catalog.tabular_sections.json with human-readable props for every TS."""
    result = {}
    for ts_entry in ts_list[2:]:
        ts_name = _ts_name(ts_entry)
        props = _ts_props(ts_entry)
        col_list = ts_entry[2]  # [col_type_uuid, count, col_entry1, ...]
        columns = {}
        for col_entry in col_list[2:]:
            cname = _col_name(col_entry)
            columns[cname] = _col_props(col_entry)
        props['columns'] = columns
        result[ts_name] = props
    path = os.path.join(catalog_dir, CATALOG_TABULAR_SECTIONS_JSON)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_tabular_section(source_dir, catalog_name, ts_name, ts_source_catalog_dir):
    """Add a tabular section to a catalog in a v8unpack source directory.

    Args:
        source_dir:             Path to the source directory (modified in-place).
        catalog_name:           Name of the catalog folder (e.g. "Справочник01").
        ts_name:                Name of the tabular section to add.
        ts_source_catalog_dir:  Directory containing the reference Catalog.json.
    """
    # ------------------------------------------------------------------
    # 1. Read TS entry from source catalog dir
    # ------------------------------------------------------------------
    src_catalog_json = os.path.join(ts_source_catalog_dir, CATALOG_JSON)
    if not os.path.isfile(src_catalog_json):
        raise FileNotFoundError(
            f'Catalog.json not found in {ts_source_catalog_dir!r}')

    src_data = _load_json(src_catalog_json)
    src_ts_list = _get_ts_list(src_data)

    ts_entry = None
    for entry in src_ts_list[2:]:
        if _ts_name(entry) == ts_name:
            ts_entry = entry
            break

    if ts_entry is None:
        raise ValueError(
            f'Tabular section {ts_name!r} not found in {src_catalog_json!r}')

    ts_uuid = _ts_uuid(ts_entry)

    # ------------------------------------------------------------------
    # 2. Insert TS into target Catalog.json
    # ------------------------------------------------------------------
    dst_catalog_json = os.path.join(
        source_dir, 'Catalog', catalog_name, CATALOG_JSON)
    if not os.path.isfile(dst_catalog_json):
        raise FileNotFoundError(
            f'Target Catalog.json not found: {dst_catalog_json!r}')

    dst_data = _load_json(dst_catalog_json)
    dst_ts_list = _get_ts_list(dst_data)

    # Check if TS already present
    for entry in dst_ts_list[2:]:
        if _ts_name(entry) == ts_name:
            print(f'[add_tabular_section] ТЧ {ts_name!r} уже присутствует, пропускаем.')
            return

    # Increment count and append entry
    count = int(str(dst_ts_list[1]))
    dst_ts_list[1] = str(count + 1)
    dst_ts_list.append(ts_entry)

    _save_json(dst_catalog_json, dst_data)
    _rebuild_tabular_sections_json(
        os.path.join(source_dir, 'Catalog', catalog_name), dst_ts_list)
    print(f'[add_tabular_section] Каталог {catalog_name!r}: добавлена ТЧ '
          f'{ts_name!r} (uuid={ts_uuid}), всего ТЧ: {count + 1}'
          f' [обновлён {CATALOG_TABULAR_SECTIONS_JSON}]')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Add a tabular section to a catalog in a v8unpack source directory.'
    )
    parser.add_argument('source_dir', help='Path to the source directory to modify')
    parser.add_argument('catalog_name', help='Catalog folder name')
    parser.add_argument('ts_name', help='Name of the tabular section to add')
    parser.add_argument('ts_source_catalog_dir',
                        help='Directory containing the source Catalog.json')
    args = parser.parse_args()
    add_tabular_section(args.source_dir, args.catalog_name,
                        args.ts_name, args.ts_source_catalog_dir)


if __name__ == '__main__':
    _main()
