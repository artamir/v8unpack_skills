"""Tests for v8-cf-add-attribute skill.

TestAddAttributeFiles
    Verifies that add_attribute correctly updates Catalog.json.

TestAddAttributeCFRoundtrip
    Full pipeline: copy source → add_attribute → v8unpack build → v8unpack extract.
    Verifies the attribute is present in the extracted output.
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

from add_attribute import add_attribute  # noqa: E402

ATTRS_LIST_PATH = ['header', 0, 6]

# (source_step, catalog_name, attr_name, attr_source_step, target_step)
_TRANSITIONS = [
    (
        'step_0009',
        'Справочник01',
        'ТестРеквизитСтрока50',
        'step_0010',
        'step_0010',
    ),
    (
        'step_0011',
        'Справочник01',
        'РеквизитЧисло10_2',
        'step_0012',
        'step_0012',
    ),
    (
        'step_0009',
        'Справочник01',
        'ТестРеквизитЧисло102',
        'step_0010',
        'step_0010',
    ),
    (
        'step_0012',
        'Справочник01',
        'ТестРеквизитЧисло102',
        'step_0013',
        'step_0013',
    ),
    (
        'step_0013',
        'Справочник01',
        'Реквизит1Справочник1',
        'step_0014',
        'step_0014',
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


class TestAddAttributeFiles(unittest.TestCase):
    """add_attribute updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, attr_name, attr_source_step, target_step):
        attr_source_dir = os.path.join(_REF_SOURCES, attr_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8aa_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            count_before = int(str(_get_attrs_list(cat_before)[1]))

            add_attribute(src, catalog_name, attr_name, attr_source_dir)

            cat_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            cat_data = _load_json(cat_path)
            attrs = _get_attrs_list(cat_data)
            names = _attr_names(attrs)

            self.assertIn(attr_name, names,
                          f'Attribute {attr_name!r} must be present after add_attribute')
            self.assertEqual(str(count_before + 1), str(attrs[1]),
                             'Count must be incremented by 1')

            # Verify Catalog.attributes.json
            attrs_json_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.attributes.json')
            self.assertTrue(os.path.isfile(attrs_json_path),
                            'Catalog.attributes.json must be created by add_attribute')
            attrs_json = _load_json(attrs_json_path)
            self.assertIn(attr_name, attrs_json,
                          f'{attr_name!r} must appear in Catalog.attributes.json')
            props = attrs_json[attr_name]
            self.assertIn('uuid', props, 'props must have uuid')
            self.assertIn('synonym', props, 'props must have synonym')
            self.assertIn('type', props, 'props must have type')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0010_ТестРеквизитСтрока50(self):
        """step_0009 --[add_attribute(ТестРеквизитСтрока50)]--> step_0010"""
        self._run(*_TRANSITIONS[0])

    def test_step_0012_РеквизитЧисло10_2(self):
        """step_0011 --[add_attribute(РеквизитЧисло10_2)]--> step_0012"""
        self._run(*_TRANSITIONS[1])

    def test_step_0010_ТестРеквизитЧисло102(self):
        """step_0009 --[add_attribute(ТестРеквизитЧисло102)]--> step_0010"""
        self._run(*_TRANSITIONS[2])

    def test_step_0013_ТестРеквизитЧисло102(self):
        """step_0012 --[add_attribute(ТестРеквизитЧисло102)]--> step_0013"""
        self._run(*_TRANSITIONS[3])

    def test_step_0014_Реквизит1Справочник1(self):
        """step_0013 --[add_attribute(Реквизит1Справочник1)]--> step_0014"""
        self._run(*_TRANSITIONS[4])


class TestAddAttributeCFRoundtrip(unittest.TestCase):
    """Full pipeline: add_attribute + build + extract → attribute present."""

    def _run(self, source_step, catalog_name, attr_name, attr_source_step, target_step):
        attr_source_dir = os.path.join(_REF_SOURCES, attr_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8aa_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            add_attribute(src, catalog_name, attr_name, attr_source_dir)

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
            self.assertIn(
                attr_name,
                names,
                f'Attribute {attr_name!r} must be present after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0010_ТестРеквизитСтрока50(self):
        """step_0009 --[add_attribute(ТестРеквизитСтрока50)]--> step_0010: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])

    def test_step_0012_РеквизитЧисло10_2(self):
        """step_0011 --[add_attribute(РеквизитЧисло10_2)]--> step_0012: CF roundtrip OK"""
        self._run(*_TRANSITIONS[1])

    def test_step_0010_ТестРеквизитЧисло102(self):
        """step_0009 --[add_attribute(ТестРеквизитЧисло102)]--> step_0010: CF roundtrip OK"""
        self._run(*_TRANSITIONS[2])

    def test_step_0013_ТестРеквизитЧисло102(self):
        """step_0012 --[add_attribute(ТестРеквизитЧисло102)]--> step_0013: CF roundtrip OK"""
        self._run(*_TRANSITIONS[3])

    def test_step_0014_Реквизит1Справочник1(self):
        """step_0013 --[add_attribute(Реквизит1Справочник1)]--> step_0014: CF roundtrip OK"""
        self._run(*_TRANSITIONS[4])


if __name__ == '__main__':
    unittest.main(verbosity=2)
