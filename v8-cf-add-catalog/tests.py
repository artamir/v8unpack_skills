"""Tests for v8-cf-add-catalog skill.

TestAddCatalogFiles
    Verifies that add_catalog creates the correct files in the source directory.

TestAddCatalogCFRoundtrip
    Full pipeline: copy source → add_catalog → v8unpack build → v8unpack extract.
    Verifies the catalog is present in the extracted output.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(__file__)
_REPO = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))
_TOOLS = os.path.join(_HERE, 'tools')
_V8UNPACK_SRC = os.path.join(_REPO, 'vendor', 'v8unpack', 'src')
_REF_SOURCES = os.path.join(_REPO, 'ref_sources')

sys.path.insert(0, _TOOLS)
sys.path.insert(0, _V8UNPACK_SRC)

from add_catalog import add_catalog  # noqa: E402

# (source_step, catalog_name, catalog_data_dir_relative_to_ref_step, target_step)
_TRANSITIONS = [
    (
        'step_0005',
        'Справочник1',
        os.path.join('step_0006', 'Catalog', 'Справочник1'),
        'step_0006',
    ),
    (
        'step_0008',
        'Справочник01',
        os.path.join('step_0009', 'Catalog', 'Справочник01'),
        'step_0009',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class TestAddCatalogFiles(unittest.TestCase):
    """add_catalog creates correct files and updates Configuration.json."""

    def _run(self, source_step, catalog_name, catalog_data_rel, target_step):
        catalog_data_dir = os.path.join(_REF_SOURCES, catalog_data_rel)
        tmp = tempfile.mkdtemp(prefix='v8ac_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            add_catalog(src, catalog_name, catalog_data_dir)

            # Verify Catalog.id.json
            id_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.id.json')
            self.assertTrue(os.path.isfile(id_path),
                            f'Catalog.id.json not found: {id_path}')
            id_data = _load_json(id_path)
            self.assertIn('uuid', id_data, 'Catalog.id.json must have "uuid"')
            catalog_uuid = id_data['uuid']

            # Verify Catalog.json
            cat_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            self.assertTrue(os.path.isfile(cat_path),
                            f'Catalog.json not found: {cat_path}')

            # Verify v8unpack_include_order.json
            order_path = os.path.join(src, 'Catalog', 'v8unpack_include_order.json')
            self.assertTrue(os.path.isfile(order_path),
                            'v8unpack_include_order.json not found')
            order_data = _load_json(order_path)
            self.assertIn(catalog_uuid, order_data.get('uuids', []),
                          f'Catalog UUID {catalog_uuid!r} not in include_order')

            # Verify Configuration.json catalogs list
            cfg = _load_json(os.path.join(src, 'Configuration.json'))
            catalogs_list = cfg['header'][0][4][1][1][16]
            self.assertIn(catalog_uuid, catalogs_list,
                          f'Catalog UUID {catalog_uuid!r} not in Configuration.json '
                          f'catalogs list')

            # Compare with target_step reference
            ref_cfg = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Configuration.json')
            )
            ref_catalogs_list = ref_cfg['header'][0][4][1][1][16]
            self.assertEqual(
                ref_catalogs_list,
                catalogs_list,
                f'{source_step} --[add_catalog({catalog_name})]-- {target_step}: '
                'catalogs list mismatch in Configuration.json',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0006(self):
        """step_0005 --[add_catalog(Справочник1)]--> step_0006: files and config correct"""
        self._run(*_TRANSITIONS[0])

    def test_step_0009(self):
        """step_0008 --[add_catalog(Справочник01)]--> step_0009: files and config correct"""
        self._run(*_TRANSITIONS[1])


class TestAddCatalogCFRoundtrip(unittest.TestCase):
    """Full pipeline: add_catalog + build + extract → catalog present in extracted output."""

    def _run(self, source_step, catalog_name, catalog_data_rel, target_step):
        catalog_data_dir = os.path.join(_REF_SOURCES, catalog_data_rel)
        tmp = tempfile.mkdtemp(prefix='v8ac_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract  # noqa: E402

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            add_catalog(src, catalog_name, catalog_data_dir)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            # Verify catalog directory exists in extracted output
            catalog_dir = os.path.join(unpacked, 'Catalog', catalog_name)
            self.assertTrue(
                os.path.isdir(catalog_dir),
                f'Catalog directory not found after roundtrip: {catalog_dir}',
            )

            # Verify Catalog.id.json UUID matches
            id_data = _load_json(os.path.join(unpacked, 'Catalog', catalog_name, 'Catalog.id.json'))
            catalog_data_id = _load_json(os.path.join(catalog_data_dir, 'Catalog.id.json'))
            self.assertEqual(
                catalog_data_id['uuid'],
                id_data.get('uuid'),
                f'Catalog UUID mismatch after roundtrip: '
                f'expected {catalog_data_id["uuid"]!r}, got {id_data.get("uuid")!r}',
            )

            # Verify catalog UUID is in Configuration.json catalogs list
            cfg = _load_json(os.path.join(unpacked, 'Configuration.json'))
            catalogs_list = cfg['header'][0][4][1][1][16]
            self.assertIn(
                catalog_data_id['uuid'],
                catalogs_list,
                f'Catalog UUID not in Configuration.json catalogs list after roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0006(self):
        """step_0005 --[add_catalog(Справочник1)]--> step_0006: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])

    def test_step_0009(self):
        """step_0008 --[add_catalog(Справочник01)]--> step_0009: CF roundtrip OK"""
        self._run(*_TRANSITIONS[1])


if __name__ == '__main__':
    import unittest
    unittest.main(verbosity=2)
