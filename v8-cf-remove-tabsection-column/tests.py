"""Tests for v8-cf-remove-tabsection-column skill.

TestRemoveTabsectionColumnFiles
    Verifies that remove_tabsection_column correctly updates Catalog.json
    and rewrites Catalog.tabular_sections.json.

TestRemoveTabsectionColumnCFRoundtrip
    Full pipeline: copy source → remove_tabsection_column → v8unpack build → v8unpack extract.
    Verifies the column is absent in the extracted output.
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

from remove_tabsection_column import remove_tabsection_column  # noqa: E402

TS_LIST_PATH = ['header', 0, 5]

# (source_step, catalog_name, ts_name, col_name, target_step)
_TRANSITIONS = [
    (
        'step_0034',
        'Справочник01',
        'ТабличнаяЧасть1',
        'Реквизит1Строка10',
        'step_0035',
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


def _find_ts(ts_list, ts_name):
    for entry in ts_list[2:]:
        if entry[0][1][5][1][2].strip('"') == ts_name:
            return entry
    return None


def _col_names(ts_entry):
    col_list = ts_entry[2]
    return [entry[0][1][1][1][2].strip('"') for entry in col_list[2:]]


class TestRemoveTabsectionColumnFiles(unittest.TestCase):
    """remove_tabsection_column updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, ts_name, col_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rtsc_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_before = _find_ts(_get_ts_list(cat_before), ts_name)
            self.assertIsNotNone(ts_before,
                                 f'TS {ts_name!r} must exist before removing column')
            self.assertIn(col_name, _col_names(ts_before),
                          f'Column {col_name!r} must exist before removal')

            remove_tabsection_column(src, catalog_name, ts_name, col_name)

            cat_after = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_list_after = _get_ts_list(cat_after)
            ts_after = _find_ts(ts_list_after, ts_name)
            self.assertIsNotNone(ts_after)
            col_names_after = _col_names(ts_after)

            self.assertNotIn(col_name, col_names_after,
                             f'Column {col_name!r} must be absent after removal')
            self.assertEqual(str(len(col_names_after)), str(ts_after[2][1]),
                             'Column count in TS must match actual number of entries')

            # Verify Catalog.tabular_sections.json
            ts_json_path = os.path.join(src, 'Catalog', catalog_name,
                                        'Catalog.tabular_sections.json')
            self.assertTrue(os.path.isfile(ts_json_path),
                            'Catalog.tabular_sections.json must be updated')
            ts_json = _load_json(ts_json_path)
            self.assertIn(ts_name, ts_json)
            cols = ts_json[ts_name].get('columns', {})
            self.assertNotIn(col_name, cols,
                             f'{col_name!r} must NOT appear in columns after removal')

            # Compare column count with target_step reference
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog', catalog_name, 'Catalog.json')
            )
            ref_ts = _find_ts(_get_ts_list(ref_cat), ts_name)
            self.assertIsNotNone(ref_ts)
            self.assertEqual(
                ref_ts[2][1],
                ts_after[2][1],
                f'{source_step} --[remove_tabsection_column({ts_name}, {col_name})]-- {target_step}: '
                'column count mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0035_Реквизит1Строка10(self):
        """step_0034 --[remove_tabsection_column(ТабличнаяЧасть1, Реквизит1Строка10)]--> step_0035"""
        self._run(*_TRANSITIONS[0])


class TestRemoveTabsectionColumnCFRoundtrip(unittest.TestCase):
    """Full pipeline: remove_tabsection_column + build + extract → column absent."""

    def _run(self, source_step, catalog_name, ts_name, col_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rtsc_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            remove_tabsection_column(src, catalog_name, ts_name, col_name)

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
            self.assertNotIn(
                col_name,
                _col_names(ts_entry),
                f'Column {col_name!r} must be absent after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0035_Реквизит1Строка10(self):
        """step_0034 --[remove_tabsection_column(ТЧ1, Рекв1Строка10)]--> step_0035: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
