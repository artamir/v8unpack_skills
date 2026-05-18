"""Add a catalog (Справочник) to a v8unpack source directory.

The tool copies the catalog definition files into the target directory and
updates Configuration.json to register the new catalog.

Usage:
    python add_catalog.py <source_dir> <catalog_name> <catalog_data_dir>

Arguments:
    source_dir       Path to the v8unpack source directory to modify.
    catalog_name     Name of the catalog (e.g. "Справочник1").
    catalog_data_dir Directory that contains Catalog.json and Catalog.id.json
                     for the catalog being added (e.g. ref_sources/step_0006/Catalog/Справочник1).

The tool modifies source_dir in-place:
  - Creates  Catalog/<catalog_name>/Catalog.id.json
  - Creates  Catalog/<catalog_name>/Catalog.json
  - Creates/updates  Catalog/v8unpack_include_order.json
  - Updates  Configuration.json  (registers catalog UUID in the catalogs list)
"""
import argparse
import bisect
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


def _update_outer_timestamps(source_dir, catalog_uuid):
    """Add catalog_uuid to .v8unpack_outer_timestamps.json (inner container 1).

    v8unpack uses _file_order.json restored from this file to decide which
    binary objects get packed into the CF.  Without this update the newly
    created catalog binary would be silently skipped during packing.
    """
    ts_path = os.path.join(source_dir, OUTER_TIMESTAMPS_FILE)
    if not os.path.isfile(ts_path):
        return  # No timestamps file — build will fall back to sorted dir listing

    ts = _load_json(ts_path)
    container = ts.get(_INNER_CONTAINER_IDX)
    if not container:
        return

    changed = False

    # _file_times.json — add UUID with a timestamp copied from existing entries
    file_times = container.get('_file_times.json', {})
    if catalog_uuid not in file_times:
        all_ts = [v.get('created_raw', 0) for v in file_times.values()
                  if isinstance(v, dict)]
        ref_ts = max(all_ts) if all_ts else 0
        file_times[catalog_uuid] = {'created_raw': ref_ts, 'modified_raw': ref_ts}
        container['_file_times.json'] = file_times
        changed = True

    # _file_order.json — insert UUID maintaining sorted order
    file_order = container.get('_file_order.json', [])
    if catalog_uuid not in file_order:
        bisect.insort(file_order, catalog_uuid)
        container['_file_order.json'] = file_order
        changed = True

    # _toc_order.json — insert UUID maintaining sorted order
    toc_order = container.get('_toc_order.json', [])
    if catalog_uuid not in toc_order:
        bisect.insort(toc_order, catalog_uuid)
        container['_toc_order.json'] = toc_order
        changed = True

    if changed:
        ts[_INNER_CONTAINER_IDX] = container
        _save_json(ts_path, ts)
        print(f'[add_catalog] Обновлён {OUTER_TIMESTAMPS_FILE}: добавлен {catalog_uuid}')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_catalog(source_dir, catalog_name, catalog_data_dir):
    """Add a catalog to a v8unpack source directory.

    Args:
        source_dir:       Path to the source directory (modified in-place).
        catalog_name:     Name of the catalog folder (e.g. "Справочник1").
        catalog_data_dir: Directory containing Catalog.json and Catalog.id.json.
    """
    # ------------------------------------------------------------------
    # 1. Read catalog UUID from Catalog.id.json
    # ------------------------------------------------------------------
    id_json_src = os.path.join(catalog_data_dir, 'Catalog.id.json')
    if not os.path.isfile(id_json_src):
        raise FileNotFoundError(f'Catalog.id.json not found in {catalog_data_dir!r}')

    id_data = _load_json(id_json_src)
    catalog_uuid = id_data.get('uuid')
    if not catalog_uuid:
        raise ValueError(f'Missing "uuid" in {id_json_src!r}')

    catalog_json_src = os.path.join(catalog_data_dir, 'Catalog.json')
    if not os.path.isfile(catalog_json_src):
        raise FileNotFoundError(f'Catalog.json not found in {catalog_data_dir!r}')

    # ------------------------------------------------------------------
    # 2. Copy catalog definition files into source_dir
    # ------------------------------------------------------------------
    catalog_dst_dir = os.path.join(source_dir, 'Catalog', catalog_name)
    os.makedirs(catalog_dst_dir, exist_ok=True)
    shutil.copy2(id_json_src, os.path.join(catalog_dst_dir, 'Catalog.id.json'))
    shutil.copy2(catalog_json_src, os.path.join(catalog_dst_dir, 'Catalog.json'))
    print(f'[add_catalog] Скопированы файлы справочника "{catalog_name}" '
          f'(uuid={catalog_uuid})')

    # ------------------------------------------------------------------
    # 3. Create/update Catalog/v8unpack_include_order.json
    # ------------------------------------------------------------------
    catalog_dir = os.path.join(source_dir, 'Catalog')
    order_path = os.path.join(catalog_dir, INCLUDE_ORDER_FILE)
    if os.path.isfile(order_path):
        order_data = _load_json(order_path)
        uuids = order_data.get('uuids', [])
        if catalog_uuid not in uuids:
            uuids.append(catalog_uuid)
        order_data['uuids'] = uuids
    else:
        order_data = {'uuids': [catalog_uuid]}

    _save_json(order_path, order_data)
    print(f'[add_catalog] Обновлён {INCLUDE_ORDER_FILE}: uuids={order_data["uuids"]}')

    # ------------------------------------------------------------------
    # 4. Update Configuration.json — register catalog in catalogs list
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
        print(f'[add_catalog] Справочник уже зарегистрирован в Configuration.json '
              f'(uuid={catalog_uuid}), пропускаем.')
    else:
        # Increment count (index 1) and append uuid
        count = int(catalogs_list[1])
        catalogs_list[1] = str(count + 1)
        catalogs_list.append(catalog_uuid)
        _save_json(cfg_path, cfg)
        print(f'[add_catalog] Configuration.json обновлён: '
              f'catalogs_count={count + 1}, добавлен {catalog_uuid}')

    # ------------------------------------------------------------------
    # 5. Update .v8unpack_outer_timestamps.json so the new catalog binary
    #    gets included when v8unpack packs the CF.
    # ------------------------------------------------------------------
    _update_outer_timestamps(source_dir, catalog_uuid)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Add a catalog to a v8unpack source directory.'
    )
    parser.add_argument('source_dir', help='Path to the source directory to modify')
    parser.add_argument('catalog_name', help='Name of the catalog (e.g. Справочник1)')
    parser.add_argument(
        'catalog_data_dir',
        help='Directory containing Catalog.json and Catalog.id.json'
    )
    args = parser.parse_args()

    add_catalog(args.source_dir, args.catalog_name, args.catalog_data_dir)


if __name__ == '__main__':
    _main()
