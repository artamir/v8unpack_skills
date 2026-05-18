"""Tests for v8-cf-remove-attribute skill.

TestRemoveAttributeFiles
    Verifies that remove_attribute correctly updates Catalog.json.

TestRemoveAttributeCFRoundtrip
    Full pipeline: copy source → remove_attribute → v8unpack build → v8unpack extract.
    Verifies the attribute is absent in the extracted output.
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

from remove_attribute import remove_attribute  # noqa: E402

ATTRS_LIST_PATH = ['header', 0, 6]

# (source_step, catalog_name, attr_name, target_step)
_TRANSITIONS = [
    (
        'step_0010',
        'Справочник01',
        'ТестРеквизитЧисло102',
        'step_0011',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _get_attrs_list(catalog_json_data):
    obj = catalog_json_data
    for k in ATTRS_LIST_PATH:
        obj = obj[k]
    return obj


def _attr_names(attrs_list):
    return [item[0][1][1][1][2].strip('"') for item in attrs_list[2:]]


class TestRemoveAttributeFiles(unittest.TestCase):
    """remove_attribute updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, attr_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8ra_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            names_before = _attr_names(_get_attrs_list(cat_before))
            self.assertIn(attr_name, names_before,
                          f'Attribute {attr_name!r} must exist before removal')

            remove_attribute(src, catalog_name, attr_name)

            cat_after = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            attrs_after = _get_attrs_list(cat_after)
            names_after = _attr_names(attrs_after)

            self.assertNotIn(attr_name, names_after,
                             f'Attribute {attr_name!r} must be absent after removal')
            self.assertEqual(str(len(names_after)), str(attrs_after[1]),
                             'Count in attrs list must match actual number of entries')

            # Verify Catalog.attributes.json
            attrs_json_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.attributes.json')
            self.assertTrue(os.path.isfile(attrs_json_path),
                            'Catalog.attributes.json must be updated by remove_attribute')
            attrs_json = _load_json(attrs_json_path)
            self.assertNotIn(attr_name, attrs_json,
                             f'{attr_name!r} must NOT appear in Catalog.attributes.json after removal')

            # Compare with target_step reference
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog', catalog_name, 'Catalog.json')
            )
            ref_attrs = _get_attrs_list(ref_cat)
            self.assertEqual(
                ref_attrs[1],
                attrs_after[1],
                f'{source_step} --[remove_attribute({attr_name})]-- {target_step}: '
                'attribute count mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0011_ТестРеквизитЧисло102(self):
        """step_0010 --[remove_attribute(ТестРеквизитЧисло102)]--> step_0011"""
        self._run(*_TRANSITIONS[0])


class TestRemoveAttributeCFRoundtrip(unittest.TestCase):
    """Full pipeline: remove_attribute + build + extract → attribute absent."""

    def _run(self, source_step, catalog_name, attr_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8ra_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            remove_attribute(src, catalog_name, attr_name)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            cat_data = _load_json(
                os.path.join(unpacked, 'Catalog', catalog_name, 'Catalog.json')
            )
            attrs = _get_attrs_list(cat_data)
            names = _attr_names(attrs)
            self.assertNotIn(
                attr_name,
                names,
                f'Attribute {attr_name!r} must be absent after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0011_ТестРеквизитЧисло102(self):
        """step_0010 --[remove_attribute(ТестРеквизитЧисло102)]--> step_0011: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
