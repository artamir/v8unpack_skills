"""Tests for v8-cf-remove-form skill.

TestRemoveFormFiles
    Verifies that remove_form correctly removes form files and updates Catalog.json.

TestRemoveFormCFRoundtrip
    Full pipeline: copy source → remove_form → v8unpack build → compare bytes.
    step_0016 passes byte-exact roundtrip, so this test compares against the ref CF.
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

from remove_form import remove_form  # noqa: E402

# (source_step, catalog_name, form_name, target_step)
_TRANSITIONS = [
    (
        'step_0015',
        'Справочник01',
        'ФормаЭлемента',
        'step_0016',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class TestRemoveFormFiles(unittest.TestCase):
    """remove_form removes form files and updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, form_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rf_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            # Count forms before
            cat_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            cat_before = _load_json(cat_path)
            count_before = int(str(cat_before['header'][0][7][1]))
            form_dir_before = os.path.join(
                src, 'Catalog', catalog_name, 'CatalogForm', form_name)
            id_json = os.path.join(form_dir_before, 'CatalogForm.id.json')
            form_uuid = _load_json(id_json)['uuid']

            remove_form(src, catalog_name, form_name)

            # Check form directory was removed
            form_dir = os.path.join(
                src, 'Catalog', catalog_name, 'CatalogForm', form_name)
            self.assertFalse(
                os.path.exists(form_dir),
                f'Form directory must be removed: {form_dir}')

            # Check CatalogForm/ was removed (no other forms)
            catalog_form_dir = os.path.join(
                src, 'Catalog', catalog_name, 'CatalogForm')
            self.assertFalse(
                os.path.exists(catalog_form_dir),
                'CatalogForm directory must be removed when empty')

            # Check Catalog.json was updated
            cat_data = _load_json(cat_path)
            forms_list = cat_data['header'][0][7]
            count_after = int(str(forms_list[1]))
            self.assertEqual(count_after, count_before - 1,
                             'Form count must be decremented by 1')
            self.assertNotIn(form_uuid, forms_list,
                             'Form UUID must not appear in header[0][7]')

            # Check element form slot in header[0][1] was zeroed
            h1 = cat_data['header'][0][1]
            self.assertNotIn(form_uuid, h1,
                             'Form UUID must not appear in header[0][1] after removal')

            # Verify result matches ref step_0016 Catalog.json
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog',
                             catalog_name, 'Catalog.json'))
            self.assertEqual(
                cat_data['header'][0][7],
                ref_cat['header'][0][7],
                'header[0][7] must match ref step after remove_form')
            self.assertEqual(
                cat_data['header'][0][1],
                ref_cat['header'][0][1],
                'header[0][1] must match ref step after remove_form')

        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0016_ФормаЭлемента(self):
        """step_0015 --[remove_form(ФормаЭлемента)]--> step_0016"""
        self._run(*_TRANSITIONS[0])


class TestRemoveFormCFRoundtrip(unittest.TestCase):
    """Full pipeline: remove_form + build + extract → form absent."""

    def _run(self, source_step, catalog_name, form_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rf_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            remove_form(src, catalog_name, form_name)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            # Verify form directory is absent after extract
            form_dir = os.path.join(
                unpacked, 'Catalog', catalog_name, 'CatalogForm', form_name)
            self.assertFalse(
                os.path.exists(form_dir),
                f'Form directory must be absent after build+extract: {form_dir}')

            # Verify Catalog.json shows 0 forms
            cat_data = _load_json(
                os.path.join(unpacked, 'Catalog', catalog_name, 'Catalog.json'))
            forms_list = cat_data['header'][0][7]
            count = int(str(forms_list[1]))
            self.assertEqual(count, 0, 'Form count must be 0 after build+extract')

        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0016_ФормаЭлемента(self):
        """step_0015 --[remove_form(ФормаЭлемента)]--> build → byte-identical to ref CF"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    unittest.main()
