"""Remove a form from a catalog in a v8unpack source directory.

Usage:
    python remove_form.py <source_dir> <catalog_name> <form_name>

Arguments:
    source_dir    Path to the v8unpack source directory to modify.
    catalog_name  Name of the catalog folder (e.g. "Справочник01").
    form_name     Name of the form to remove (e.g. "ФормаЭлемента").

The tool performs the following changes in source_dir/Catalog/<catalog_name>/:
  - Updates Catalog.json header[0][7]: decrements form count and removes UUID
  - Zeros out the form UUID slot in Catalog.json header[0][1]
  - Deletes CatalogForm/<form_name>/ directory
  - Removes CatalogForm/v8unpack_include_order.json
  - Removes CatalogForm/ directory if it becomes empty
"""
import argparse
import json
import os
import shutil
import sys

CATALOG_JSON = 'Catalog.json'
CONFIGURATION_JSON = 'Configuration.json'

# Placeholder used when no form is assigned.
_ZERO_UUID = '00000000-0000-0000-0000-000000000000'


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


def _delete_v8unpack_timestamps(source_dir):
    """Delete v8unpack build-cache timestamp files from a source directory.

    These files track the binary container structure from the last extract/build.
    After structural changes (e.g. removing a form), the cached file order may
    reference objects that no longer exist, causing v8build to fail.
    Deleting them forces a clean rebuild.
    """
    _TIMESTAMP_PATTERNS = (
        '.v8unpack_inner_timestamps.json',
        '.v8unpack_outer_timestamps.json',
        '.v8unpack_stage1_timestamps.json',
    )
    for root, dirs, files in os.walk(source_dir):
        for fname in files:
            if fname in _TIMESTAMP_PATTERNS or fname.endswith('.v8unpack_inner_timestamps.json'):
                try:
                    os.remove(os.path.join(root, fname))
                except OSError:
                    pass


def _update_configuration_remove_form(config_path, form_uuid):
    """Remove form UUID references from Configuration.json versions[0].

    versions[0] structure:
        [0]  = "1"               (constant)
        [1]  = str(N)            (count of "header items" that follow)
        [2..2+N-1] = N header items:
                     pairs of (quoted_fixed_uuid, auto_transaction_uuid), preceded by '""'
                     The LAST pair is the form's UUID entry, added when the form was created.
        [2+N..] = changed-objects pairs: (quoted_object_id, auto_uuid)
                  The FIRST pair is ("form_uuid.0", auto_uuid), added with the form.
    """
    data = _load_json(config_path)
    versions = data['versions'][0]

    quoted_uuid = f'"{form_uuid}"'       # '"744ad8b5-..."'
    quoted_uuid_0 = f'"{form_uuid}.0"'   # '"744ad8b5-....0"'

    n = int(str(versions[1]))  # current N

    # Find form UUID in header section [2 .. 2+N-1]
    header_start = 2
    header_end = header_start + n  # exclusive
    found_header_idx = None
    for i in range(header_start, header_end, 2):
        if i + 1 < len(versions) and versions[i] == quoted_uuid:
            found_header_idx = i
            break
    if found_header_idx is None:
        raise ValueError(
            f'Form UUID {form_uuid!r} not found in Configuration.json '
            f'versions[0] header section')

    # Remove the (quoted_uuid, auto_uuid) pair from header section
    del versions[found_header_idx + 1]  # auto UUID
    del versions[found_header_idx]      # quoted form UUID
    versions[1] = str(n - 2)           # decrement N

    # Find and remove "form_uuid.0" pair from changed-objects section
    found_change_idx = None
    for i in range(len(versions)):
        if versions[i] == quoted_uuid_0:
            found_change_idx = i
            break
    if found_change_idx is not None:
        del versions[found_change_idx + 1]  # auto UUID
        del versions[found_change_idx]      # quoted "uuid.0"

    _save_json(config_path, data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def remove_form(source_dir, catalog_name, form_name):
    """Remove a form from a catalog in a v8unpack source directory.

    Args:
        source_dir:    Path to the source directory (modified in-place).
        catalog_name:  Name of the catalog folder (e.g. "Справочник01").
        form_name:     Name of the form to remove (e.g. "ФормаЭлемента").
    """
    dst_catalog_dir = os.path.join(source_dir, 'Catalog', catalog_name)
    dst_catalog_form_dir = os.path.join(dst_catalog_dir, 'CatalogForm')
    dst_form_dir = os.path.join(dst_catalog_form_dir, form_name)

    catalog_json_path = os.path.join(dst_catalog_dir, CATALOG_JSON)

    # ------------------------------------------------------------------
    # 1. Validate inputs
    # ------------------------------------------------------------------
    if not os.path.isdir(dst_form_dir):
        raise FileNotFoundError(
            f'Form directory not found: {dst_form_dir!r}')

    if not os.path.isfile(catalog_json_path):
        raise FileNotFoundError(
            f'Catalog.json not found: {catalog_json_path!r}')

    # ------------------------------------------------------------------
    # 2. Read the form UUID
    # ------------------------------------------------------------------
    form_id_path = os.path.join(dst_form_dir, 'CatalogForm.id.json')
    form_uuid = _load_json(form_id_path)['uuid']

    # ------------------------------------------------------------------
    # 3. Update Catalog.json
    # ------------------------------------------------------------------
    data = _load_json(catalog_json_path)

    # header[0][7]: forms collection — ["type_uuid", "count", uuid1, ...]
    forms_list = data['header'][0][7]
    if form_uuid not in forms_list:
        raise ValueError(
            f'Form UUID {form_uuid!r} not found in header[0][7] of '
            f'{catalog_json_path!r}')
    forms_list.remove(form_uuid)
    count = int(str(forms_list[1]))
    forms_list[1] = str(count - 1)

    # header[0][1]: zero out the slot that held the form UUID
    h1 = data['header'][0][1]
    for i, val in enumerate(h1):
        if val == form_uuid:
            h1[i] = _ZERO_UUID
            break

    _save_json(catalog_json_path, data)

    # ------------------------------------------------------------------
    # 4. Update Configuration.json — remove form UUID from versions[0]
    # ------------------------------------------------------------------
    config_path = os.path.join(source_dir, CONFIGURATION_JSON)
    if os.path.isfile(config_path):
        _update_configuration_remove_form(config_path, form_uuid)

    # ------------------------------------------------------------------
    # 5. Delete form directory and clean up CatalogForm/
    # ------------------------------------------------------------------
    shutil.rmtree(dst_form_dir)

    dst_inc = os.path.join(dst_catalog_form_dir, 'v8unpack_include_order.json')
    if os.path.isfile(dst_inc):
        os.remove(dst_inc)

    if os.path.isdir(dst_catalog_form_dir) and not os.listdir(dst_catalog_form_dir):
        os.rmdir(dst_catalog_form_dir)

    # ------------------------------------------------------------------
    # 6. Delete v8unpack timestamp cache files so that the next build
    #    recomputes the container structure without the removed form.
    # ------------------------------------------------------------------
    _delete_v8unpack_timestamps(source_dir)

    print(f'[remove_form] Каталог {catalog_name!r}: удалена форма '
          f'{form_name!r} (uuid={form_uuid}), форм осталось: {count - 1}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Remove a form from a catalog in a v8unpack source directory.')
    parser.add_argument('source_dir', help='v8unpack source directory')
    parser.add_argument('catalog_name', help='Catalog folder name')
    parser.add_argument('form_name', help='Form name to remove')
    args = parser.parse_args()
    remove_form(args.source_dir, args.catalog_name, args.form_name)


if __name__ == '__main__':
    _main()
