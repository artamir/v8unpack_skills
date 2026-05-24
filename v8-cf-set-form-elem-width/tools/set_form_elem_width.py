"""Set width of an element on an ordinary 1C form (CatalogForm.elem.json).

Usage:
    python set_form_elem_width.py <source_dir> <catalog_name> <form_name> <elem_name> <new_width>

Arguments:
    source_dir    Path to the v8unpack source directory.
    catalog_name  Catalog folder name (e.g. "Справочник01").
    form_name     Form name (e.g. "ФормаЭлемента").
    elem_name     Element name on the form (e.g. "Код").
    new_width     New width in pixels (positive integer).

The tool modifies two files in
    source_dir/Catalog/<catalog_name>/CatalogForm/<form_name>/:

  CatalogForm.elem.json:
    data["<page>/<elem>"]["raw"][3][3]      — absolute pixel width (str)
    data["<page>/<elem>"]["raw"][3][9][1][3] — right-anchor offset (str),
        updated by the same delta so the anchor stays consistent.
        Only updated when the anchor is active (ref != -1).

  CatalogForm.json:
    form[0][0][1][10]                       — form revision counter (str),
        incremented by 1 on every Designer edit.

Backups (<file>.bak) are created before any modification.
"""
import argparse
import json
import os
import shutil
import sys

_FORM_JSON = 'CatalogForm.json'
_FORM_ELEM_JSON = 'CatalogForm.elem.json'


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


def _backup(path):
    bak = path + '.bak'
    shutil.copy2(path, bak)
    return bak


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _find_elem_key(data_keys, elem_name):
    """Return the full data key for elem_name (e.g. 'Страница1/Код' for 'Код').

    First tries an exact match, then searches for keys whose last path segment
    equals elem_name.
    """
    if elem_name in data_keys:
        return elem_name
    for key in data_keys:
        if '/' in key and key.rsplit('/', 1)[-1] == elem_name:
            return key
    return None


def set_elem_width(elem_json_path, form_json_path, elem_name, new_width):
    """Apply the width change to elem.json and form.json.

    Raises ValueError if the element is not found.
    Returns (old_width, new_width, key).
    """
    elem_data = _load_json(elem_json_path)
    form_data = _load_json(form_json_path)

    data = elem_data.get('data', {})
    key = _find_elem_key(list(data.keys()), elem_name)
    if key is None:
        raise ValueError(
            'Element %r not found in %s\nAvailable keys: %s' % (
                elem_name, elem_json_path,
                ', '.join(k for k in data if '/' in k),
            )
        )

    raw = data[key]['raw']
    # raw layout (index 3): ['8', x, y, w, h, 1, anchor_L, anchor_T,
    #                         anchor_R, anchor_W, anchor_H5, anchor_H6, ...]
    geo = raw[3]
    old_width = int(geo[3])
    delta = new_width - old_width

    if delta == 0:
        print('[set_form_elem_width] Width is already %d, no change.' % new_width)
        return old_width, new_width, key

    # 1. Update absolute pixel width
    geo[3] = str(new_width)

    # 2. Update right-anchor offset (geo[9] = anchor_W)
    #    Structure: ['0', ['2', ref_idx, side, offset], ['2', '-1', '6', '0']]
    #    Only update when the anchor is active (ref != '-1').
    anchor_w = geo[9]
    if anchor_w[1][1] != '-1':
        old_off = int(anchor_w[1][3])
        anchor_w[1][3] = str(old_off + delta)

    # 3. Increment form revision counter: form[0][0][1][10]
    form = form_data['form']
    old_rev = int(form[0][0][1][10])
    form[0][0][1][10] = str(old_rev + 1)

    # 4. Save with backups
    _backup(elem_json_path)
    _backup(form_json_path)
    _save_json(elem_json_path, elem_data)
    _save_json(form_json_path, form_data)

    print('[set_form_elem_width] %s: width %d -> %d (anchor delta=%+d)' % (
        key, old_width, new_width, delta))
    print('[set_form_elem_width] Form revision: %d -> %d' % (old_rev, old_rev + 1))

    return old_width, new_width, key


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Set width of an element on an ordinary 1C form.')
    parser.add_argument('source_dir', help='v8unpack source directory')
    parser.add_argument('catalog_name', help='Catalog folder name (e.g. Справочник01)')
    parser.add_argument('form_name', help='Form name (e.g. ФормаЭлемента)')
    parser.add_argument('elem_name', help='Element name on the form (e.g. Код)')
    parser.add_argument('new_width', type=int, help='New width in pixels')
    args = parser.parse_args()

    if args.new_width <= 0:
        print('Error: new_width must be a positive integer.', file=sys.stderr)
        sys.exit(1)

    form_dir = os.path.join(
        args.source_dir, 'Catalog', args.catalog_name,
        'CatalogForm', args.form_name,
    )
    if not os.path.isdir(form_dir):
        print('Error: form directory not found: %s' % form_dir, file=sys.stderr)
        sys.exit(1)

    elem_json = os.path.join(form_dir, _FORM_ELEM_JSON)
    form_json = os.path.join(form_dir, _FORM_JSON)
    for path in [elem_json, form_json]:
        if not os.path.isfile(path):
            print('Error: file not found: %s' % path, file=sys.stderr)
            sys.exit(1)

    try:
        set_elem_width(elem_json, form_json, args.elem_name, args.new_width)
    except ValueError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    _main()
