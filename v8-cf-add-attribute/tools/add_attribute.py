"""Add an attribute (Реквизит) to a catalog in a v8unpack source directory.

The attribute definition is read from a reference catalog directory and
inserted into the target catalog's Catalog.json.

Usage:
    python add_attribute.py <source_dir> <catalog_name> <attr_name> <attr_source_catalog_dir>

Arguments:
    source_dir              Path to the v8unpack source directory to modify.
    catalog_name            Name of the catalog folder (e.g. "Справочник01").
    attr_name               Name of the attribute to add (e.g. "ТестРеквизитСтрока50").
    attr_source_catalog_dir Directory containing the source Catalog.json (e.g.
                            ref_sources/step_0010/Catalog/Справочник01).

The tool modifies source_dir/Catalog/<catalog_name>/Catalog.json in-place:
  - Appends the attribute entry to header[0][6]
  - Increments the attribute count at header[0][6][1]
"""
import argparse
import json
import os
import sys

CATALOG_JSON = 'Catalog.json'
CATALOG_ATTRIBUTES_JSON = 'Catalog.attributes.json'

# Path inside Catalog.json that holds the user-defined attributes list.
# Format: ["<type_uuid>", "<count>", attr_entry1, attr_entry2, ...]
ATTRS_LIST_PATH = ['header', 0, 6]


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


def _get_attrs_list(catalog_data):
    """Navigate to and return the attributes list within a Catalog.json structure."""
    obj = catalog_data
    for key in ATTRS_LIST_PATH:
        obj = obj[key]
    return obj  # ["type_uuid", "count", entry1, entry2, ...]


def _attr_name(item):
    """Extract the attribute name from an attribute list entry."""
    # item[0][1] = ['27', ['2', ['3', ['1', '0', UUID], '"NAME"', ...] ...] ...]
    return item[0][1][1][1][2].strip('"')


def _attr_uuid(item):
    """Extract the attribute UUID from an attribute list entry."""
    return item[0][1][1][1][1][2]


# ---------------------------------------------------------------------------
# Attribute property parsing
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
    """Parse type_pattern list to a human-readable dict.

    Examples:
        ['"Pattern"', ['"S"', '50', '1']]  -> {kind: String, length: 50}
        ['"Pattern"', ['"N"', '10', '2', '0']] -> {kind: Number, digits: 10, precision: 2}
    """
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


def _attr_props(item):
    """Parse raw attribute entry to a human-readable properties dict.

    Returns a dict with keys: uuid, synonym, type, indexing, use, fill_check.
    """
    meta = item[0][1][1][1]   # ['3', uuid_holder, '"name"', synonym, ...]
    uuid = meta[1][2]
    synonym = _parse_synonym(meta[3])
    type_props = _parse_type(item[0][1][1][2])
    pb = item[0][1]  # props block
    return {
        'uuid': uuid,
        'synonym': synonym,
        'type': type_props,
        'indexing': str(pb[7]) if len(pb) > 7 else '0',
        'use': _unwrap_tag(pb[8]) if len(pb) > 8 else 'U',
        'fill_check': _unwrap_tag(pb[9]) if len(pb) > 9 else 'U',
    }


def _rebuild_attributes_json(catalog_dir, attrs_list):
    """Write Catalog.attributes.json with human-readable props for every attribute."""
    props = {}
    for item in attrs_list[2:]:
        name = _attr_name(item)
        props[name] = _attr_props(item)
    path = os.path.join(catalog_dir, CATALOG_ATTRIBUTES_JSON)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_attribute(source_dir, catalog_name, attr_name, attr_source_catalog_dir):
    """Add an attribute to a catalog in a v8unpack source directory.

    Args:
        source_dir:              Path to the source directory (modified in-place).
        catalog_name:            Name of the catalog folder (e.g. "Справочник01").
        attr_name:               Name of the attribute to add.
        attr_source_catalog_dir: Directory containing the reference Catalog.json.
    """
    # ------------------------------------------------------------------
    # 1. Read attribute entry from source catalog dir
    # ------------------------------------------------------------------
    src_catalog_json = os.path.join(attr_source_catalog_dir, CATALOG_JSON)
    if not os.path.isfile(src_catalog_json):
        raise FileNotFoundError(
            f'Catalog.json not found in {attr_source_catalog_dir!r}')

    src_data = _load_json(src_catalog_json)
    src_attrs = _get_attrs_list(src_data)
    src_items = src_attrs[2:]  # skip type_uuid and count

    attr_entry = None
    for item in src_items:
        if _attr_name(item) == attr_name:
            attr_entry = item
            break

    if attr_entry is None:
        raise ValueError(
            f'Attribute {attr_name!r} not found in {src_catalog_json!r}')

    attr_uuid = _attr_uuid(attr_entry)

    # ------------------------------------------------------------------
    # 2. Insert attribute into target Catalog.json
    # ------------------------------------------------------------------
    dst_catalog_json = os.path.join(
        source_dir, 'Catalog', catalog_name, CATALOG_JSON)
    if not os.path.isfile(dst_catalog_json):
        raise FileNotFoundError(
            f'Target Catalog.json not found: {dst_catalog_json!r}')

    dst_data = _load_json(dst_catalog_json)
    dst_attrs = _get_attrs_list(dst_data)

    # Check if attribute already present
    for item in dst_attrs[2:]:
        if _attr_name(item) == attr_name:
            print(f'[add_attribute] Атрибут {attr_name!r} уже присутствует, пропускаем.')
            return

    # Increment count and append entry
    count = int(str(dst_attrs[1]))
    dst_attrs[1] = str(count + 1)
    dst_attrs.append(attr_entry)

    _save_json(dst_catalog_json, dst_data)
    _rebuild_attributes_json(
        os.path.join(source_dir, 'Catalog', catalog_name), dst_attrs)
    print(f'[add_attribute] Каталог {catalog_name!r}: добавлен атрибут '
          f'{attr_name!r} (uuid={attr_uuid}), всего атрибутов: {count + 1}'
          f' [обновлён {CATALOG_ATTRIBUTES_JSON}]')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Add an attribute to a catalog in a v8unpack source directory.'
    )
    parser.add_argument('source_dir', help='Path to the source directory to modify')
    parser.add_argument('catalog_name', help='Catalog folder name')
    parser.add_argument('attr_name', help='Name of the attribute to add')
    parser.add_argument('attr_source_catalog_dir',
                        help='Directory containing the source Catalog.json')
    args = parser.parse_args()
    add_attribute(args.source_dir, args.catalog_name,
                  args.attr_name, args.attr_source_catalog_dir)


if __name__ == '__main__':
    _main()
