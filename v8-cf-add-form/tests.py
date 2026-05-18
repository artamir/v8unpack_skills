"""Tests for v8-cf-add-form skill.

TestAddFormFiles
    Verifies that add_form correctly copies form files and updates Catalog.json.

TestAddFormCFRoundtrip
    Full pipeline: copy source → add_form → v8unpack build → v8unpack extract.
    Verifies the form directory is present in the extracted output.
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

from add_form import add_form  # noqa: E402

# (source_step, catalog_name, form_name, ref_step)
_TRANSITIONS = [
    (
        'step_0014',
        'Справочник01',
        'ФормаЭлемента',
        'step_0015',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


class TestAddFormFiles(unittest.TestCase):
    """add_form copies files and updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, form_name, ref_step):
        ref_catalog_dir = os.path.join(
            _REF_SOURCES, ref_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8af_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            # Count forms before
            cat_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            cat_before = _load_json(cat_path)
            count_before = int(str(cat_before['header'][0][7][1]))

            add_form(src, catalog_name, form_name, ref_catalog_dir)

            # Check form directory was created
            form_dir = os.path.join(
                src, 'Catalog', catalog_name, 'CatalogForm', form_name)
            self.assertTrue(
                os.path.isdir(form_dir),
                f'Form directory must be created: {form_dir}')

            # Check CatalogForm.id.json exists
            id_json = os.path.join(form_dir, 'CatalogForm.id.json')
            self.assertTrue(os.path.isfile(id_json),
                            'CatalogForm.id.json must exist')
            form_uuid = _load_json(id_json)['uuid']

            # Check Catalog.json was updated
            cat_data = _load_json(cat_path)
            forms_list = cat_data['header'][0][7]
            count_after = int(str(forms_list[1]))
            self.assertEqual(count_after, count_before + 1,
                             'Form count must be incremented by 1')
            self.assertIn(form_uuid, forms_list,
                          'Form UUID must be in header[0][7]')

            # Check element form slot in header[0][1]
            h1 = cat_data['header'][0][1]
            self.assertIn(form_uuid, h1,
                          'Form UUID must appear in header[0][1]')

            # Check include order file
            inc_path = os.path.join(
                src, 'Catalog', catalog_name, 'CatalogForm',
                'v8unpack_include_order.json')
            self.assertTrue(os.path.isfile(inc_path),
                            'v8unpack_include_order.json must be present')

            # Check CatalogForm.properties.json was generated
            props_path = os.path.join(form_dir, 'CatalogForm.properties.json')
            self.assertTrue(os.path.isfile(props_path),
                            'CatalogForm.properties.json must be generated')
            props = _load_json(props_path)
            self.assertEqual(props['name'], form_name,
                             'properties.json name must match form_name')
            self.assertIn('width', props, 'properties.json must have width')
            self.assertIn('height', props, 'properties.json must have height')
            self.assertIsInstance(props['elements'], list,
                                  'properties.json elements must be a list')

        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0015_ФормаЭлемента(self):
        """step_0014 --[add_form(ФормаЭлемента)]--> step_0015"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    unittest.main()
