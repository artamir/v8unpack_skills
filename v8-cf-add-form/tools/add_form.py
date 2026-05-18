"""Add a form to a catalog in a v8unpack source directory.

The form directory is copied from a reference catalog directory and registered
in the target catalog's Catalog.json and Configuration.json.

Usage:
    python add_form.py <source_dir> <catalog_name> <form_name> <ref_catalog_dir>

Arguments:
    source_dir       Path to the v8unpack source directory to modify.
    catalog_name     Name of the catalog folder (e.g. "Справочник01").
    form_name        Name of the form to add (e.g. "ФормаЭлемента").
    ref_catalog_dir  Reference catalog directory containing the form to copy
                     (e.g. ref_sources/step_0015/Catalog/Справочник01).
                     The parent of the Catalog/ folder is used to locate
                     the reference Configuration.json.

The tool performs the following changes in source_dir/:
  - Copies Catalog/<catalog_name>/CatalogForm/<form_name>/ from ref_catalog_dir
  - Copies Catalog/<catalog_name>/CatalogForm/v8unpack_include_order.json
  - Updates Catalog/<catalog_name>/Catalog.json header[0][7]: adds form UUID
  - Updates Catalog/<catalog_name>/Catalog.json header[0][1][ELEMENT_FORM_SLOT]
  - Replaces Configuration.json with the one from the reference step directory
    so that versions[0] correctly references the form binary container
"""
import argparse
import json
import os
import shutil
import sys

CATALOG_JSON = 'Catalog.json'
CONFIGURATION_JSON = 'Configuration.json'
CATALOG_FORM_JSON = 'CatalogForm.json'
CATALOG_FORM_ELEM_JSON = 'CatalogForm.elem.json'
CATALOG_FORM_PROPERTIES_JSON = 'CatalogForm.properties.json'

# Fixed slot index in Catalog.json header[0][1] for the element form UUID.
# In the 1C v8 catalog format this slot is always at position 21.
_ELEMENT_FORM_SLOT = 21

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


# ---------------------------------------------------------------------------
# Form properties helpers
# ---------------------------------------------------------------------------

def rebuild_form_properties_json(form_dir):
    """Write CatalogForm.properties.json with human-readable form and element properties.

    Reads CatalogForm.json and CatalogForm.elem.json from *form_dir* and
    writes a CatalogForm.properties.json with the following structure::

        {
          "name": "ФормаЭлемента",
          "synonym": "Форма элемента",
          "comment": "",
          "form_type": "0",
          "width": 400,
          "height": 292,
          "elements": [
            {"name": "КоманднаяПанель1", "type": "CommandPanel", "page": "Страница1",
             "prop": "", "left": 0, "top": 0, "right": 400, "bottom": 25},
            ...
          ]
        }

    Args:
        form_dir: Path to the form directory containing CatalogForm.json and
                  CatalogForm.elem.json.
    """
    form_json_path = os.path.join(form_dir, CATALOG_FORM_JSON)
    form_elem_path = os.path.join(form_dir, CATALOG_FORM_ELEM_JSON)

    form_data = _load_json(form_json_path)
    elem_data = _load_json(form_elem_path)

    # Form-level dimensions: form[0][0][1][3] = width, form[0][0][1][4] = height
    dims = form_data['form'][0][0][1]
    width = int(dims[3])
    height = int(dims[4])

    synonym = form_data.get('name2', {}).get('ru', '')

    # Build elements list from tree (preserves order)
    elements = []
    for item in elem_data.get('tree', []):
        name = item['name']
        elem_type = item['type']
        page = item['page']

        page_key = f'{page}/{name}'
        data_entry = elem_data['data'].get(page_key, {})
        prop = data_entry.get('prop', '')

        raw = data_entry.get('raw', [])
        elem = {'name': name, 'type': elem_type, 'page': page, 'prop': prop}
        if (len(raw) > 3 and isinstance(raw[3], list)
                and len(raw[3]) >= 5 and raw[3][0] == '8'):
            geo = raw[3]
            elem['left'] = int(geo[1])
            elem['top'] = int(geo[2])
            elem['right'] = int(geo[3])
            elem['bottom'] = int(geo[4])
        elements.append(elem)

    props = {
        'name': form_data.get('name', ''),
        'synonym': synonym,
        'comment': form_data.get('comment', ''),
        'form_type': str(form_data.get('Тип формы', '0')),
        'width': width,
        'height': height,
        'elements': elements,
    }

    out_path = os.path.join(form_dir, CATALOG_FORM_PROPERTIES_JSON)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_form(source_dir, catalog_name, form_name, ref_catalog_dir):
    """Add a form to a catalog in a v8unpack source directory.

    Args:
        source_dir:       Path to the source directory (modified in-place).
        catalog_name:     Name of the catalog folder (e.g. "Справочник01").
        form_name:        Name of the form to add (e.g. "ФормаЭлемента").
        ref_catalog_dir:  Reference catalog directory containing the form.
    """
    dst_catalog_dir = os.path.join(source_dir, 'Catalog', catalog_name)
    dst_catalog_form_dir = os.path.join(dst_catalog_dir, 'CatalogForm')
    dst_form_dir = os.path.join(dst_catalog_form_dir, form_name)

    ref_catalog_form_dir = os.path.join(ref_catalog_dir, 'CatalogForm')
    ref_form_dir = os.path.join(ref_catalog_form_dir, form_name)

    # ------------------------------------------------------------------
    # 1. Validate inputs
    # ------------------------------------------------------------------
    if not os.path.isdir(ref_form_dir):
        raise FileNotFoundError(
            f'Reference form directory not found: {ref_form_dir!r}')

    catalog_json_path = os.path.join(dst_catalog_dir, CATALOG_JSON)
    if not os.path.isfile(catalog_json_path):
        raise FileNotFoundError(
            f'Catalog.json not found: {catalog_json_path!r}')

    # ------------------------------------------------------------------
    # 2. Copy form directory and include-order file
    # ------------------------------------------------------------------
    os.makedirs(dst_catalog_form_dir, exist_ok=True)
    if os.path.exists(dst_form_dir):
        shutil.rmtree(dst_form_dir)
    shutil.copytree(ref_form_dir, dst_form_dir)

    ref_inc = os.path.join(ref_catalog_form_dir, 'v8unpack_include_order.json')
    dst_inc = os.path.join(dst_catalog_form_dir, 'v8unpack_include_order.json')
    if os.path.isfile(ref_inc):
        shutil.copy2(ref_inc, dst_inc)

    # ------------------------------------------------------------------
    # 3. Read the form UUID from CatalogForm.id.json
    # ------------------------------------------------------------------
    form_id_path = os.path.join(dst_form_dir, 'CatalogForm.id.json')
    form_uuid = _load_json(form_id_path)['uuid']

    # ------------------------------------------------------------------
    # 4. Update Catalog.json
    # ------------------------------------------------------------------
    data = _load_json(catalog_json_path)

    # header[0][7]: forms collection — ["type_uuid", "count", uuid1, ...]
    forms_list = data['header'][0][7]
    count = int(str(forms_list[1]))
    forms_list[1] = str(count + 1)
    forms_list.append(form_uuid)

    # header[0][1][21]: element form UUID slot
    data['header'][0][1][_ELEMENT_FORM_SLOT] = form_uuid

    _save_json(catalog_json_path, data)

    # ------------------------------------------------------------------
    # 5. Replace Configuration.json from the reference step directory
    #    so that versions[0] includes the form's binary container UUID.
    # ------------------------------------------------------------------
    # ref_catalog_dir = .../step_NNNN/Catalog/<catalog_name>
    # ref step dir    = .../step_NNNN/
    ref_step_dir = os.path.normpath(
        os.path.join(ref_catalog_dir, '..', '..'))
    ref_config = os.path.join(ref_step_dir, CONFIGURATION_JSON)
    dst_config = os.path.join(source_dir, CONFIGURATION_JSON)
    if os.path.isfile(ref_config) and os.path.isfile(dst_config):
        shutil.copy2(ref_config, dst_config)

    # ------------------------------------------------------------------
    # 6. Generate CatalogForm.properties.json
    # ------------------------------------------------------------------
    rebuild_form_properties_json(dst_form_dir)

    print(f'[add_form] Каталог {catalog_name!r}: добавлена форма '
          f'{form_name!r} (uuid={form_uuid}), форм всего: {count + 1}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(
        description='Add a form to a catalog in a v8unpack source directory.')
    parser.add_argument('source_dir', help='v8unpack source directory')
    parser.add_argument('catalog_name', help='Catalog folder name')
    parser.add_argument('form_name', help='Form name to add')
    parser.add_argument('ref_catalog_dir',
                        help='Reference catalog directory containing the form')
    args = parser.parse_args()
    add_form(args.source_dir, args.catalog_name, args.form_name,
             args.ref_catalog_dir)


if __name__ == '__main__':
    _main()
