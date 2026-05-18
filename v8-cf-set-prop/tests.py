"""Tests for v8-cf-set-prop skill.

TestSetPropProperties
    Verifies that set_prop correctly modifies Configuration.properties.json.
    Compares the result with ref_sources/<target_step>/Configuration.properties.json.

TestSetPropCFRoundtrip
    Full pipeline: copy source → set_prop → v8unpack build → v8unpack extract.
    Compares property parameters (main_launch_mode, usage_purpose) in the extracted
    Configuration.json against the reference CF content in ref_sources/<target_step>/.
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

from set_prop import set_prop  # noqa: E402
from v8unpack.v8unpack import build as v8build, extract as v8extract  # noqa: E402

_CONFIG_PARAMS_PATH = ['header', 0, 3, 1, 1]
MAIN_LAUNCH_MODE_IDX = 21
USAGE_PURPOSE_IDX = 33


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _get_config_params(config_json_path):
    """Return params list (header[0][3][1][1]) from Configuration.json."""
    data = _load_json(config_json_path)
    obj = data
    for k in _CONFIG_PARAMS_PATH:
        obj = obj[k]
    return obj


# (source_step, property, value, target_step)
_TRANSITIONS = [
    ('step_0000',   'main_launch_mode', 'ОбычноеПриложение',
     'step_0001'),
    ('step_0001',   'main_launch_mode', 'УправляемоеПриложение',
     'step_0002'),
    ('step_0002',   'main_launch_mode', 'ОбычноеПриложение',
     'step_0003'),
    ('step_0000',   'usage_purpose',
     'Приложение для платформы, Приложение для мобильной платформы',
     'step_0001_1'),
    ('step_0001_1', 'usage_purpose',    'Приложение для платформы',
     'step_0002_1'),
]


class TestSetPropProperties(unittest.TestCase):
    """set_prop produces the correct Configuration.properties.json."""

    def _run(self, source_step, prop, value, target_step):
        tmp = tempfile.mkdtemp(prefix='v8sp_props_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            set_prop(src, prop, value)

            actual = _load_json(os.path.join(src, 'Configuration.properties.json'))
            expected = _load_json(
                os.path.join(_REF_SOURCES, target_step, 'Configuration.properties.json')
            )
            self.assertEqual(
                expected, actual,
                f'{source_step} --[{prop}={value!r}]--> {target_step}: '
                'Configuration.properties.json mismatch',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _make_props_test(source_step, prop, value, target_step):
    def test_method(self):
        self._run(source_step, prop, value, target_step)
    test_method.__name__ = f'test_{target_step}'
    test_method.__doc__ = (
        f'{source_step} --[{prop}={value!r}]--> {target_step}: properties match'
    )
    return test_method


for _src, _prop, _val, _tgt in _TRANSITIONS:
    setattr(TestSetPropProperties, f'test_{_tgt}', _make_props_test(_src, _prop, _val, _tgt))


class TestSetPropCFRoundtrip(unittest.TestCase):
    """Full pipeline: set_prop + build + extract → property params match reference CF."""

    def _run(self, source_step, prop, value, target_step):
        tmp = tempfile.mkdtemp(prefix='v8sp_rt_')
        try:
            src = os.path.join(tmp, 'src')
            shutil.copytree(os.path.join(_REF_SOURCES, source_step), src)
            set_prop(src, prop, value)

            out_cf = os.path.join(tmp, 'out.cf')
            v8build(src, out_cf)

            unpacked = os.path.join(tmp, 'unpacked')
            os.makedirs(unpacked)
            v8extract(out_cf, unpacked)

            built_params = _get_config_params(
                os.path.join(unpacked, 'Configuration.json')
            )
            ref_params = _get_config_params(
                os.path.join(_REF_SOURCES, target_step, 'Configuration.json')
            )

            self.assertEqual(
                ref_params[MAIN_LAUNCH_MODE_IDX],
                built_params[MAIN_LAUNCH_MODE_IDX],
                f'{source_step}→{target_step}: main_launch_mode mismatch after CF roundtrip',
            )
            self.assertEqual(
                ref_params[USAGE_PURPOSE_IDX],
                built_params[USAGE_PURPOSE_IDX],
                f'{source_step}→{target_step}: usage_purpose mismatch after CF roundtrip',
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _make_roundtrip_test(source_step, prop, value, target_step):
    def test_method(self):
        self._run(source_step, prop, value, target_step)
    test_method.__name__ = f'test_{target_step}'
    test_method.__doc__ = (
        f'{source_step} --[{prop}={value!r}]--> {target_step}: '
        'CF roundtrip property values match'
    )
    return test_method


for _src, _prop, _val, _tgt in _TRANSITIONS:
    setattr(
        TestSetPropCFRoundtrip,
        f'test_{_tgt}',
        _make_roundtrip_test(_src, _prop, _val, _tgt),
    )


if __name__ == '__main__':
    unittest.main()
