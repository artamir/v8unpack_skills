"""Tests for v8-cf-add-tabular-section skill.

TestAddTabularSectionFiles
    Verifies that add_tabular_section correctly updates Catalog.json
    and writes Catalog.tabular_sections.json.

TestAddTabularSectionCFRoundtrip
    Full pipeline: copy source → add_tabular_section → v8unpack build → v8unpack extract.
    Verifies the TS is present in the extracted output.
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

from add_tabular_section import add_tabular_section  # noqa: E402

TS_LIST_PATH = ['header', 0, 5]

# (source_step, catalog_name, ts_name, ts_source_step, target_step)
_TRANSITIONS = [
    (
        'step_0030',
        'Справочник01',
        'ТабличнаяЧасть1',
        'step_0031',
        'step_0031',
    ),
    (
        'step_0032',
        'Справочник01',
        'ТабличнаяЧасть1',
        'step_0033',
        'step_0033',
    ),
]


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _get_ts_list(catalog_json_data):
    obj = catalog_json_data
    for k in TS_LIST_PATH:
        obj = obj[k]
    return obj


def _ts_names(ts_list):
    return [entry[0][1][5][1][2].strip('"') for entry in ts_list[2:]]


class TestAddTabularSectionFiles(unittest.TestCase):
    """add_tabular_section updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, ts_name, ts_source_step, target_step):
        ts_source_dir = os.path.join(_REF_SOURCES, ts_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8ats_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            count_before = int(str(_get_ts_list(cat_before)[1]))

            add_tabular_section(src, catalog_name, ts_name, ts_source_dir)

            cat_path = os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            cat_data = _load_json(cat_path)
            ts_list = _get_ts_list(cat_data)
            names = _ts_names(ts_list)

            self.assertIn(ts_name, names,
                          f'TS {ts_name!r} must be present after add_tabular_section')
            self.assertEqual(str(count_before + 1), str(ts_list[1]),
                             'Count must be incremented by 1')

            # Verify Catalog.tabular_sections.json
            ts_json_path = os.path.join(src, 'Catalog', catalog_name,
                                        'Catalog.tabular_sections.json')
            self.assertTrue(os.path.isfile(ts_json_path),
                            'Catalog.tabular_sections.json must be created')
            ts_json = _load_json(ts_json_path)
            self.assertIn(ts_name, ts_json,
                          f'{ts_name!r} must appear in Catalog.tabular_sections.json')
            props = ts_json[ts_name]
            self.assertIn('uuid', props, 'props must have uuid')
            self.assertIn('synonym', props, 'props must have synonym')
            self.assertIn('columns', props, 'props must have columns')

            # Compare count with target_step reference
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog', catalog_name, 'Catalog.json')
            )
            ref_ts = _get_ts_list(ref_cat)
            self.assertEqual(
                ref_ts[1],
                ts_list[1],
                f'{source_step} --[add_tabular_section({ts_name})]-- {target_step}: '
                'TS count mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0031_ТабличнаяЧасть1(self):
        """step_0030 --[add_tabular_section(ТабличнаяЧасть1)]--> step_0031"""
        self._run(*_TRANSITIONS[0])

    def test_step_0033_ТабличнаяЧасть1(self):
        """step_0032 --[add_tabular_section(ТабличнаяЧасть1)]--> step_0033"""
        self._run(*_TRANSITIONS[1])


class TestAddTabularSectionCFRoundtrip(unittest.TestCase):
    """Full pipeline: add_tabular_section + build + extract → TS present."""

    def _run(self, source_step, catalog_name, ts_name, ts_source_step, target_step):
        ts_source_dir = os.path.join(_REF_SOURCES, ts_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8ats_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            add_tabular_section(src, catalog_name, ts_name, ts_source_dir)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            cat_data = _load_json(
                os.path.join(unpacked, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_list = _get_ts_list(cat_data)
            names = _ts_names(ts_list)
            self.assertIn(
                ts_name,
                names,
                f'TS {ts_name!r} must be present after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0031_ТабличнаяЧасть1(self):
        """step_0030 --[add_tabular_section(ТабличнаяЧасть1)]--> step_0031: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])

    def test_step_0033_ТабличнаяЧасть1(self):
        """step_0032 --[add_tabular_section(ТабличнаяЧасть1)]--> step_0033: CF roundtrip OK"""
        self._run(*_TRANSITIONS[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
