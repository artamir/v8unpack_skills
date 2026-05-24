"""Set a geometric property of an element on an ordinary 1C form.

Usage:
    python set_form_elem_prop.py <source_dir> <catalog_name> <form_name> <elem_name> <prop> <new_value>

Arguments:
    source_dir    Path to the v8unpack source directory.
    catalog_name  Catalog folder name (e.g. "Справочник01").
    form_name     Form name (e.g. "ФормаЭлемента").
    elem_name     Element name on the form (e.g. "Код").
    prop          Property name: width/ширина, height/высота, left/лево, top/верх.
    new_value     New value in pixels (non-negative integer).

The tool modifies files in
    source_dir/Catalog/<catalog_name>/CatalogForm/<form_name>/:

  CatalogForm.elem.json       — geometry block (raw[3]) of the element
  CatalogForm.json            — form revision counter (form[0][0][1][10]) +1
  CatalogForm.elem-props.json — synced if the file exists (keeps it consistent
                                 with raw so v8unpack encode does not revert the change)

Anchor update rules are defined in form_elem_props.py.
Backups (<file>.bak) are created before any modification.
"""
import argparse
import json
import os
import shutil
import sys

# Resolve import whether the script is run directly from tools/ or from
# another working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from form_elem_props import resolve_prop, apply_prop, PROP_INFO  # noqa: E402

_FORM_JSON           = 'CatalogForm.json'
_FORM_ELEM_JSON      = 'CatalogForm.elem.json'
_FORM_ELEM_PROPS_JSON = 'CatalogForm.elem-props.json'


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
    shutil.copy2(path, path + '.bak')


# ---------------------------------------------------------------------------
# Element lookup
# ---------------------------------------------------------------------------

def _find_elem_key(data_keys, elem_name):
    """Return the full data key for *elem_name*, e.g. 'Страница1/Код'."""
    if elem_name in data_keys:
        return elem_name
    for key in data_keys:
        if '/' in key and key.rsplit('/', 1)[-1] == elem_name:
            return key
    return None


# ---------------------------------------------------------------------------
# Core operation
# ---------------------------------------------------------------------------

def set_elem_prop(elem_json_path, form_json_path, elem_name, prop, new_value,
                  elem_props_json_path=None):
    """Read, modify, and save elem.json + form.json for a single property change.

    Also updates elem-props.json (if it exists / *elem_props_json_path* given)
    so that it stays consistent with raw during subsequent v8unpack encode.

    Returns (key, canon_prop, old_val, new_val).
    Raises ValueError on unknown property or element not found.
    """
    canon = resolve_prop(prop)
    if canon is None:
        supported = ', '.join(
            '%s/%s' % (k, info['label_ru']) for k, info in PROP_INFO.items()
        )
        raise ValueError('Unknown property %r. Supported: %s' % (prop, supported))

    elem_data = _load_json(elem_json_path)
    form_data = _load_json(form_json_path)

    data = elem_data.get('data', {})
    key = _find_elem_key(list(data.keys()), elem_name)
    if key is None:
        available = ', '.join(k.rsplit('/', 1)[-1] for k in data if '/' in k)
        raise ValueError(
            'Element %r not found. Available: %s' % (elem_name, available)
        )

    raw = data[key]['raw']
    old_val, new_val = apply_prop(raw, canon, new_value)

    if old_val == new_val:
        print('[set_form_elem_prop] %s.%s is already %d, no change.' % (
            key, canon, new_val))
        return key, canon, old_val, new_val

    # Increment form revision counter: form[0][0][1][10]
    form = form_data['form']
    old_rev = int(form[0][0][1][10])
    form[0][0][1][10] = str(old_rev + 1)

    _backup(elem_json_path)
    _backup(form_json_path)
    _save_json(elem_json_path, elem_data)
    _save_json(form_json_path, form_data)

    # Sync CatalogForm.elem-props.json if it exists, to prevent v8unpack
    # encode from reverting the change (elem-props.json takes precedence there).
    if elem_props_json_path and os.path.isfile(elem_props_json_path):
        ru_key = PROP_INFO[canon]['label_ru']  # e.g. 'Ширина'
        try:
            ep_data = _load_json(elem_props_json_path)
            if isinstance(ep_data, dict) and key in ep_data:
                _backup(elem_props_json_path)
                ep_data[key][ru_key] = new_val
                _save_json(elem_props_json_path, ep_data)
                print('[set_form_elem_prop] elem-props.json synced: %s.%s = %d' % (
                    key, ru_key, new_val))
        except Exception as e:
            print('[set_form_elem_prop] Warning: could not sync elem-props.json: %s' % e)

    info = PROP_INFO[canon]
    print('[set_form_elem_prop] %s.%s (%s): %d -> %d' % (
        key, canon, info['label_ru'], old_val, new_val))
    print('[set_form_elem_prop] Form revision: %d -> %d' % (old_rev, old_rev + 1))

    return key, canon, old_val, new_val


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Set a geometric property of an element on an ordinary 1C form.')
    parser.add_argument('source_dir',   help='v8unpack source directory')
    parser.add_argument('catalog_name', help='Catalog folder name (e.g. Справочник01)')
    parser.add_argument('form_name',    help='Form name (e.g. ФормаЭлемента)')
    parser.add_argument('elem_name',    help='Element name on the form (e.g. Код)')
    parser.add_argument('prop',         help='Property: width/ширина, height/высота, left/лево, top/верх')
    parser.add_argument('new_value',    type=int, help='New value in pixels')
    args = parser.parse_args()

    if args.new_value < 0:
        print('Error: new_value must be non-negative.', file=sys.stderr)
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
    elem_props_json = os.path.join(form_dir, _FORM_ELEM_PROPS_JSON)
    for path in (elem_json, form_json):
        if not os.path.isfile(path):
            print('Error: file not found: %s' % path, file=sys.stderr)
            sys.exit(1)

    try:
        set_elem_prop(elem_json, form_json, args.elem_name, args.prop, args.new_value,
                      elem_props_json_path=elem_props_json)
    except ValueError as e:
        print('Error: %s' % e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    _main()
