"""Tests for v8-cf-add-tabsection-column skill.

TestAddTabsectionColumnFiles
    Verifies that add_tabsection_column correctly updates Catalog.json
    and rewrites Catalog.tabular_sections.json.

TestAddTabsectionColumnCFRoundtrip
    Full pipeline: copy source → add_tabsection_column → v8unpack build → v8unpack extract.
    Verifies the column is present in the extracted output.
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

from add_tabsection_column import add_tabsection_column  # noqa: E402

TS_LIST_PATH = ['header', 0, 5]

# (source_step, catalog_name, ts_name, col_name, col_source_step, target_step)
_TRANSITIONS = [
    (
        'step_0033',
        'Справочник01',
        'ТабличнаяЧасть1',
        'Реквизит1Строка10',
        'step_0034',
        'step_0034',
    ),
    (
        'step_0035',
        'Справочник01',
        'ТабличнаяЧасть1',
        'Реквизит1Строка10',
        'step_0036',
        'step_0036',
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


def _col_names(ts_entry):
    col_list = ts_entry[2]
    return [entry[0][1][1][1][2].strip('"') for entry in col_list[2:]]


def _find_ts(ts_list, ts_name):
    for entry in ts_list[2:]:
        if entry[0][1][5][1][2].strip('"') == ts_name:
            return entry
    return None


class TestAddTabsectionColumnFiles(unittest.TestCase):
    """add_tabsection_column updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, ts_name, col_name, col_source_step, target_step):
        col_source_dir = os.path.join(_REF_SOURCES, col_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8atsc_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_entry_before = _find_ts(_get_ts_list(cat_before), ts_name)
            self.assertIsNotNone(ts_entry_before,
                                 f'TS {ts_name!r} must exist before adding column')
            count_before = int(str(ts_entry_before[2][1]))

            add_tabsection_column(src, catalog_name, ts_name, col_name, col_source_dir)

            cat_after = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_list_after = _get_ts_list(cat_after)
            ts_entry_after = _find_ts(ts_list_after, ts_name)
            self.assertIsNotNone(ts_entry_after)
            col_names_after = _col_names(ts_entry_after)

            self.assertIn(col_name, col_names_after,
                          f'Column {col_name!r} must be present after add_tabsection_column')
            self.assertEqual(str(count_before + 1), str(ts_entry_after[2][1]),
                             'Column count must be incremented by 1')

            # Verify Catalog.tabular_sections.json
            ts_json_path = os.path.join(src, 'Catalog', catalog_name,
                                        'Catalog.tabular_sections.json')
            self.assertTrue(os.path.isfile(ts_json_path),
                            'Catalog.tabular_sections.json must be updated')
            ts_json = _load_json(ts_json_path)
            self.assertIn(ts_name, ts_json, f'{ts_name!r} must appear in ts json')
            cols = ts_json[ts_name].get('columns', {})
            self.assertIn(col_name, cols,
                          f'{col_name!r} must appear in columns of Catalog.tabular_sections.json')
            col_props = cols[col_name]
            self.assertIn('uuid', col_props, 'column props must have uuid')
            self.assertIn('type', col_props, 'column props must have type')

            # Compare column count with target_step reference
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog', catalog_name, 'Catalog.json')
            )
            ref_ts = _find_ts(_get_ts_list(ref_cat), ts_name)
            self.assertIsNotNone(ref_ts)
            self.assertEqual(
                ref_ts[2][1],
                ts_entry_after[2][1],
                f'{source_step} --[add_tabsection_column({ts_name}, {col_name})]-- {target_step}: '
                'column count mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0034_Реквизит1Строка10(self):
        """step_0033 --[add_tabsection_column(ТабличнаяЧасть1, Реквизит1Строка10)]--> step_0034"""
        self._run(*_TRANSITIONS[0])

    def test_step_0036_Реквизит1Строка10(self):
        """step_0035 --[add_tabsection_column(ТабличнаяЧасть1, Реквизит1Строка10)]--> step_0036"""
        self._run(*_TRANSITIONS[1])


class TestAddTabsectionColumnCFRoundtrip(unittest.TestCase):
    """Full pipeline: add_tabsection_column + build + extract → column present."""

    def _run(self, source_step, catalog_name, ts_name, col_name, col_source_step, target_step):
        col_source_dir = os.path.join(_REF_SOURCES, col_source_step, 'Catalog', catalog_name)
        tmp = tempfile.mkdtemp(prefix='v8atsc_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            add_tabsection_column(src, catalog_name, ts_name, col_name, col_source_dir)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            cat_data = _load_json(
                os.path.join(unpacked, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_entry = _find_ts(_get_ts_list(cat_data), ts_name)
            self.assertIsNotNone(ts_entry, f'TS {ts_name!r} must be present after CF roundtrip')
            self.assertIn(
                col_name,
                _col_names(ts_entry),
                f'Column {col_name!r} must be present after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0034_Реквизит1Строка10(self):
        """step_0033 --[add_tabsection_column(ТЧ1, Рекв1Строка10)]--> step_0034: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])

    def test_step_0036_Реквизит1Строка10(self):
        """step_0035 --[add_tabsection_column(ТЧ1, Рекв1Строка10)]--> step_0036: CF roundtrip OK"""
        self._run(*_TRANSITIONS[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
