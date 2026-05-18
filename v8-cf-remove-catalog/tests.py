"""Tests for v8-cf-remove-catalog skill.

TestRemoveCatalogFiles
    Verifies that remove_catalog removes the correct files from the source directory
    and updates Configuration.json and .v8unpack_outer_timestamps.json.

TestRemoveCatalogCFRoundtrip
    Full pipeline: copy source → remove_catalog → v8unpack build → v8unpack extract.
    Verifies the catalog is absent in the extracted output.
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

from remove_catalog import remove_catalog  # noqa: E402

# (source_step, catalog_name, target_step)
_TRANSITIONS = [
    (
        'step_0006',
        'Справочник1',
        'step_0007',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class TestRemoveCatalogFiles(unittest.TestCase):
    """remove_catalog removes correct files and updates Configuration.json."""

    def _run(self, source_step, catalog_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rc_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            # Confirm catalog exists before removal
            catalog_dir_before = os.path.join(src, 'Catalog', catalog_name)
            self.assertTrue(
                os.path.isdir(catalog_dir_before),
                f'Catalog directory must exist before removal: {catalog_dir_before}',
            )
            id_data = _load_json(
                os.path.join(catalog_dir_before, 'Catalog.id.json')
            )
            catalog_uuid = id_data['uuid']

            remove_catalog(src, catalog_name)

            # Verify catalog directory is gone
            catalog_dir_after = os.path.join(src, 'Catalog', catalog_name)
            self.assertFalse(
                os.path.isdir(catalog_dir_after),
                f'Catalog directory must be removed: {catalog_dir_after}',
            )

            # Verify Configuration.json catalogs list
            cfg = _load_json(os.path.join(src, 'Configuration.json'))
            catalogs_list = cfg['header'][0][4][1][1][16]
            self.assertNotIn(
                catalog_uuid,
                catalogs_list,
                f'Catalog UUID {catalog_uuid!r} must not be in Configuration.json '
                f'catalogs list after removal',
            )

            # Compare with target_step reference
            ref_cfg = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Configuration.json')
            )
            ref_catalogs_list = ref_cfg['header'][0][4][1][1][16]
            self.assertEqual(
                ref_catalogs_list,
                catalogs_list,
                f'{source_step} --[remove_catalog({catalog_name})]-- {target_step}: '
                'catalogs list mismatch in Configuration.json',
            )

            # Verify .v8unpack_outer_timestamps.json — UUID removed from container 1
            ts_path = os.path.join(src, OUTER_TIMESTAMPS_FILE)
            if os.path.isfile(ts_path):
                ts = _load_json(ts_path)
                container = ts.get('1', {})
                file_order = container.get('_file_order.json', [])
                self.assertNotIn(
                    catalog_uuid,
                    file_order,
                    f'UUID {catalog_uuid!r} must not be in _file_order.json after removal',
                )
                toc_order = container.get('_toc_order.json', [])
                self.assertNotIn(
                    catalog_uuid,
                    toc_order,
                    f'UUID {catalog_uuid!r} must not be in _toc_order.json after removal',
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0007(self):
        """step_0006 --[remove_catalog(Справочник1)]--> step_0007: files and config correct"""
        self._run(*_TRANSITIONS[0])


OUTER_TIMESTAMPS_FILE = '.v8unpack_outer_timestamps.json'


class TestRemoveCatalogCFRoundtrip(unittest.TestCase):
    """Full pipeline: remove_catalog + build + extract → catalog absent in extracted output."""

    def _run(self, source_step, catalog_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rc_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract  # noqa: E402

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            # Get UUID before removal for later assertion
            id_data = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.id.json')
            )
            catalog_uuid = id_data['uuid']

            remove_catalog(src, catalog_name)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            # Verify catalog directory is absent in extracted output
            catalog_dir = os.path.join(unpacked, 'Catalog', catalog_name)
            self.assertFalse(
                os.path.isdir(catalog_dir),
                f'Catalog directory must be absent after roundtrip: {catalog_dir}',
            )

            # Verify catalog UUID is NOT in Configuration.json catalogs list
            cfg = _load_json(os.path.join(unpacked, 'Configuration.json'))
            catalogs_list = cfg['header'][0][4][1][1][16]
            self.assertNotIn(
                catalog_uuid,
                catalogs_list,
                f'Catalog UUID must not be in Configuration.json catalogs list after roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0007(self):
        """step_0006 --[remove_catalog(Справочник1)]--> step_0007: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    import unittest
    unittest.main(verbosity=2)
