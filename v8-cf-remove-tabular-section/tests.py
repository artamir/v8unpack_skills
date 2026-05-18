"""Tests for v8-cf-remove-tabular-section skill.

TestRemoveTabularSectionFiles
    Verifies that remove_tabular_section correctly updates Catalog.json
    and rewrites Catalog.tabular_sections.json.

TestRemoveTabularSectionCFRoundtrip
    Full pipeline: copy source → remove_tabular_section → v8unpack build → v8unpack extract.
    Verifies the TS is absent in the extracted output.
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

from remove_tabular_section import remove_tabular_section  # noqa: E402

TS_LIST_PATH = ['header', 0, 5]

# (source_step, catalog_name, ts_name, target_step)
_TRANSITIONS = [
    (
        'step_0031',
        'Справочник01',
        'ТабличнаяЧасть1',
        'step_0032',
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


class TestRemoveTabularSectionFiles(unittest.TestCase):
    """remove_tabular_section updates Catalog.json correctly."""

    def _run(self, source_step, catalog_name, ts_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rts_files_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)

            cat_before = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            names_before = _ts_names(_get_ts_list(cat_before))
            self.assertIn(ts_name, names_before,
                          f'TS {ts_name!r} must exist before removal')

            remove_tabular_section(src, catalog_name, ts_name)

            cat_after = _load_json(
                os.path.join(src, 'Catalog', catalog_name, 'Catalog.json')
            )
            ts_after = _get_ts_list(cat_after)
            names_after = _ts_names(ts_after)

            self.assertNotIn(ts_name, names_after,
                             f'TS {ts_name!r} must be absent after removal')
            self.assertEqual(str(len(names_after)), str(ts_after[1]),
                             'Count in TS list must match actual number of entries')

            # Verify Catalog.tabular_sections.json
            ts_json_path = os.path.join(src, 'Catalog', catalog_name,
                                        'Catalog.tabular_sections.json')
            self.assertTrue(os.path.isfile(ts_json_path),
                            'Catalog.tabular_sections.json must be updated')
            ts_json = _load_json(ts_json_path)
            self.assertNotIn(ts_name, ts_json,
                             f'{ts_name!r} must NOT appear in Catalog.tabular_sections.json')

            # Compare count with target_step reference
            ref_cat = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Catalog', catalog_name, 'Catalog.json')
            )
            ref_ts = _get_ts_list(ref_cat)
            self.assertEqual(
                ref_ts[1],
                ts_after[1],
                f'{source_step} --[remove_tabular_section({ts_name})]-- {target_step}: '
                'TS count mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0032_ТабличнаяЧасть1(self):
        """step_0031 --[remove_tabular_section(ТабличнаяЧасть1)]--> step_0032"""
        self._run(*_TRANSITIONS[0])


class TestRemoveTabularSectionCFRoundtrip(unittest.TestCase):
    """Full pipeline: remove_tabular_section + build + extract → TS absent."""

    def _run(self, source_step, catalog_name, ts_name, target_step):
        tmp = tempfile.mkdtemp(prefix='v8rts_rt_')
        try:
            from v8unpack.v8unpack import build as v8build, extract as v8extract

            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            remove_tabular_section(src, catalog_name, ts_name)

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
            self.assertNotIn(
                ts_name,
                names,
                f'TS {ts_name!r} must be absent after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_step_0032_ТабличнаяЧасть1(self):
        """step_0031 --[remove_tabular_section(ТабличнаяЧасть1)]--> step_0032: CF roundtrip OK"""
        self._run(*_TRANSITIONS[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
