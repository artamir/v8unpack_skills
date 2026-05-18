"""Remove a catalog (Справочник) from a v8unpack source directory.

Usage:
    python remove_catalog.py <source_dir> <catalog_name>

Arguments:
    source_dir    Path to the v8unpack source directory to modify.
    catalog_name  Name of the catalog to remove (e.g. "Справочник1").

The tool modifies source_dir in-place:
  - Removes  Catalog/<catalog_name>/
  - Updates  Catalog/v8unpack_include_order.json  (removes UUID;
             deletes the file if the list becomes empty)
  - Removes  Catalog/  if it becomes empty
  - Updates  Configuration.json  (removes catalog UUID from the catalogs list)
  - Updates  .v8unpack_outer_timestamps.json  (removes UUID from _file_order,
             _toc_order, _file_times in the inner metadata container)
"""
import argparse
import json
import os
import shutil
import sys

CONFIG_FILE = 'Configuration.json'
INCLUDE_ORDER_FILE = 'v8unpack_include_order.json'
OUTER_TIMESTAMPS_FILE = '.v8unpack_outer_timestamps.json'

# Index of the inner metadata container in the CF binary.
_INNER_CONTAINER_IDX = '1'

# Path inside Configuration.json that holds the catalogs list.
# Format: ["<type_uuid>", "<count>", "<catalog_uuid1>", ...]
CATALOGS_LIST_PATH = ['header', 0, 4, 1, 1, 16]


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


def _remove_from_outer_timestamps(source_dir, catalog_uuid):
    """Remove catalog_uuid from .v8unpack_outer_timestamps.json (inner container 1).

    v8unpack uses _file_order.json restored from this file to decide which
    binary objects get packed into the CF.  Without this removal the deleted
    catalog UUID remains in the list, which can cause build errors.
    """
    ts_path = os.path.join(source_dir, OUTER_TIMESTAMPS_FILE)
    if not os.path.isfile(ts_path):
        return

    ts = _load_json(ts_path)
    container = ts.get(_INNER_CONTAINER_IDX)
    if not container:
        return

    changed = False

    # _file_times.json — remove UUID entry
    file_times = container.get('_file_times.json', {})
    if catalog_uuid in file_times:
        del file_times[catalog_uuid]
        container['_file_times.json'] = file_times
        changed = True

    # _file_order.json — remove UUID
    file_order = container.get('_file_order.json', [])
    if catalog_uuid in file_order:
        file_order.remove(catalog_uuid)
        container['_file_order.json'] = file_order
        changed = True

    # _toc_order.json — remove UUID
    toc_order = container.get('_toc_order.json', [])
    if catalog_uuid in toc_order:
        toc_order.remove(catalog_uuid)
        container['_toc_order.json'] = toc_order
        changed = True

    if changed:
        ts[_INNER_CONTAINER_IDX] = container
        _save_json(ts_path, ts)
        print(f'[remove_catalog] Обновлён {OUTER_TIMESTAMPS_FILE}: удалён {catalog_uuid}')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def remove_catalog(source_dir, catalog_name):
    """Remove a catalog from a v8unpack source directory.

    Args:
        source_dir:    Path to the source directory (modified in-place).
        catalog_name:  Name of the catalog folder to remove (e.g. "Справочник1").
    """
    # ------------------------------------------------------------------
    # 1. Read catalog UUID from Catalog.id.json
    # ------------------------------------------------------------------
    catalog_dir = os.path.join(source_dir, 'Catalog', catalog_name)
    id_json_path = os.path.join(catalog_dir, 'Catalog.id.json')
    if not os.path.isdir(catalog_dir):
        raise FileNotFoundError(
            f'Catalog directory not found: {catalog_dir!r}')
    if not os.path.isfile(id_json_path):
        raise FileNotFoundError(
            f'Catalog.id.json not found: {id_json_path!r}')

    id_data = _load_json(id_json_path)
    catalog_uuid = id_data.get('uuid')
    if not catalog_uuid:
        raise ValueError(f'Missing "uuid" in {id_json_path!r}')

    # ------------------------------------------------------------------
    # 2. Remove catalog directory
    # ------------------------------------------------------------------
    shutil.rmtree(catalog_dir)
    print(f'[remove_catalog] Удалена директория "{catalog_name}" (uuid={catalog_uuid})')

    # ------------------------------------------------------------------
    # 3. Update Catalog/v8unpack_include_order.json
    # ------------------------------------------------------------------
    parent_catalog_dir = os.path.join(source_dir, 'Catalog')
    order_path = os.path.join(parent_catalog_dir, INCLUDE_ORDER_FILE)
    if os.path.isfile(order_path):
        order_data = _load_json(order_path)
        uuids = order_data.get('uuids', [])
        if catalog_uuid in uuids:
            uuids.remove(catalog_uuid)
        if uuids:
            order_data['uuids'] = uuids
            _save_json(order_path, order_data)
            print(f'[remove_catalog] Обновлён {INCLUDE_ORDER_FILE}: uuids={uuids}')
        else:
            # No catalogs left — remove the file
            os.remove(order_path)
            print(f'[remove_catalog] Удалён {INCLUDE_ORDER_FILE} (список пуст)')

    # Remove Catalog/ directory itself if now empty
    if os.path.isdir(parent_catalog_dir) and not os.listdir(parent_catalog_dir):
        os.rmdir(parent_catalog_dir)
        print('[remove_catalog] Удалена директория Catalog/ (стала пустой)')

    # ------------------------------------------------------------------
    # 4. Update Configuration.json — remove catalog from catalogs list
    # ------------------------------------------------------------------
    cfg_path = os.path.join(source_dir, CONFIG_FILE)
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f'{CONFIG_FILE} not found in {source_dir!r}')

    cfg = _load_json(cfg_path)

    # Navigate to the catalogs list
    obj = cfg
    for key in CATALOGS_LIST_PATH:
        obj = obj[key]
    catalogs_list = obj  # ["type_uuid", "count", "uuid1", ...]

    if catalog_uuid in catalogs_list:
        count = int(catalogs_list[1])
        catalogs_list[1] = str(count - 1)
        catalogs_list.remove(catalog_uuid)
        _save_json(cfg_path, cfg)
        print(f'[remove_catalog] Configuration.json обновлён: '
              f'catalogs_count={count - 1}, удалён {catalog_uuid}')
    else:
        print(f'[remove_catalog] UUID {catalog_uuid!r} не найден в Configuration.json, '
              f'пропускаем.')

    # ------------------------------------------------------------------
    # 5. Update .v8unpack_outer_timestamps.json
    # ------------------------------------------------------------------
    _remove_from_outer_timestamps(source_dir, catalog_uuid)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Remove a catalog from a v8unpack source directory.'
    )
    parser.add_argument('source_dir', help='Path to the source directory to modify')
    parser.add_argument('catalog_name', help='Name of the catalog to remove')
    args = parser.parse_args()

    remove_catalog(args.source_dir, args.catalog_name)


if __name__ == '__main__':
    _main()
