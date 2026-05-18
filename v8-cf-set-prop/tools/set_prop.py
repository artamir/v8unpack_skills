"""Set a configuration property in Configuration.properties.json.

If Configuration.properties.json is missing or doesn't contain the requested
property key, the tool extracts current values from Configuration.json first,
then applies the requested change.

Usage:
    python set_prop.py <source_dir> <property> <value>

Examples:
    python set_prop.py src/MyConf main_launch_mode УправляемоеПриложение
    python set_prop.py src/MyConf usage_purpose "Приложение для платформы"
    python set_prop.py src/MyConf usage_purpose "Приложение для платформы, Приложение для мобильной платформы"
"""
import argparse
import json
import os
import sys

PROPERTIES_FILE = 'Configuration.properties.json'
CONFIG_FILE = 'Configuration.json'

# Path inside Configuration.json to the parameters array
CONFIG_PARAMS_PATH = ['header', 0, 3, 1, 1]
MAIN_LAUNCH_MODE_INDEX = 21
USAGE_PURPOSE_INDEX = 33
USAGE_PURPOSE_UUID = '1708fdaa-cbce-4289-b373-07a5a74bee91'

MAIN_LAUNCH_MODE_BY_NAME = {
    'управляемоеприложение': '1',
    'managed': '1',
    'managedapplication': '1',
    '1': '1',
    'обычноеприложение': '0',
    'ordinary': '0',
    'ordinaryapplication': '0',
    '0': '0',
}

MAIN_LAUNCH_MODE_DISPLAY = {
    '1': 'УправляемоеПриложение',
    '0': 'ОбычноеПриложение',
}

USAGE_PURPOSE_BY_NAME = {
    'приложениедляплатформы': '1',
    'platform': '1',
    '1': '1',
    'приложениедлямобильнойплатформы': '2',
    'mobile': '2',
    'мобильная': '2',
    '2': '2',
}

USAGE_PURPOSE_DISPLAY = {
    '1': 'Приложение для платформы',
    '2': 'Приложение для мобильной платформы',
}

PROPERTY_ALIASES = {
    'main_launch_mode': 'main_launch_mode',
    'основнойрежимзапуска': 'main_launch_mode',
    'launchmode': 'main_launch_mode',
    'usage_purpose': 'usage_purpose',
    'назначениеиспользования': 'usage_purpose',
    'usagepurpose': 'usage_purpose',
}


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def _get_params(config_data):
    """Return the params list at CONFIG_PARAMS_PATH, or None."""
    obj = config_data
    try:
        for k in CONFIG_PARAMS_PATH:
            obj = obj[k]
    except (KeyError, IndexError, TypeError):
        return None
    return obj if isinstance(obj, list) else None


# ---------------------------------------------------------------------------
# Properties helpers
# ---------------------------------------------------------------------------

def _augment_from_config(props, source_dir):
    """Add missing property keys by reading Configuration.json.

    Called when Configuration.properties.json exists but was produced by an
    older v8unpack that didn't extract certain keys.
    """
    cfg_path = os.path.join(source_dir, CONFIG_FILE)
    if not os.path.isfile(cfg_path):
        return

    config = _load_json(cfg_path)
    params = _get_params(config)
    if not params:
        return

    if 'main_launch_mode' not in props and len(params) > MAIN_LAUNCH_MODE_INDEX:
        props['main_launch_mode'] = str(params[MAIN_LAUNCH_MODE_INDEX])
        print(f'[set_prop] Извлечено из {CONFIG_FILE}: main_launch_mode = {props["main_launch_mode"]}')

    if 'usage_purpose_indices' not in props and len(params) > USAGE_PURPOSE_INDEX:
        block = params[USAGE_PURPOSE_INDEX]
        if isinstance(block, list):
            indices = []
            for item in block[1:]:
                if (isinstance(item, list) and len(item) >= 3
                        and item[0] == '"#"' and item[1] == USAGE_PURPOSE_UUID):
                    indices.append(str(item[2]))
            if indices:
                props['usage_purpose_indices'] = indices
                props['usage_purpose_names'] = [
                    USAGE_PURPOSE_DISPLAY.get(i, f'Неизвестное ({i})')
                    for i in indices
                ]
                print(f'[set_prop] Извлечено из {CONFIG_FILE}: usage_purpose_indices = {indices}')


def ensure_properties(source_dir):
    """Load Configuration.properties.json, creating it from Configuration.json if absent."""
    props_path = os.path.join(source_dir, PROPERTIES_FILE)
    if os.path.isfile(props_path):
        props = _load_json(props_path)
    else:
        cfg_path = os.path.join(source_dir, CONFIG_FILE)
        if not os.path.isfile(cfg_path):
            raise FileNotFoundError(
                f'Не найден ни {PROPERTIES_FILE}, ни {CONFIG_FILE} в «{source_dir}»'
            )
        props = {
            'schema': 'v8unpack.configuration-properties.v1',
            'source': CONFIG_FILE,
            'raw_paths': {
                'main_launch_mode': f'header[0][3][1][1][{MAIN_LAUNCH_MODE_INDEX}]',
                'usage_purpose': f'header[0][3][1][1][{USAGE_PURPOSE_INDEX}]',
            },
        }
        print(f'[set_prop] {PROPERTIES_FILE} не найден, создаётся из {CONFIG_FILE}')

    _augment_from_config(props, source_dir)
    return props


# ---------------------------------------------------------------------------
# Setters
# ---------------------------------------------------------------------------

def _normalize_property(prop):
    key = prop.lower().replace(' ', '').replace('_', '')
    return PROPERTY_ALIASES.get(key) or PROPERTY_ALIASES.get(prop.lower())


def _set_main_launch_mode(props, value):
    key = value.lower().replace(' ', '').replace('_', '')
    raw = MAIN_LAUNCH_MODE_BY_NAME.get(key)
    if raw is None:
        allowed = ', '.join(
            f'"{v}"' for v in
            ['УправляемоеПриложение', 'ОбычноеПриложение', 'managed', 'ordinary', '0', '1']
        )
        raise ValueError(f'Неизвестное значение «{value}». Допустимые: {allowed}')
    props['main_launch_mode'] = raw
    return MAIN_LAUNCH_MODE_DISPLAY.get(raw, raw)


def _set_usage_purpose(props, value):
    parts = [v.strip() for v in value.split(',') if v.strip()]
    indices = []
    for part in parts:
        key = part.lower().replace(' ', '').replace('_', '')
        raw = USAGE_PURPOSE_BY_NAME.get(key)
        if raw is None:
            allowed = ', '.join(
                f'"{v}"' for v in [
                    'Приложение для платформы', 'Приложение для мобильной платформы',
                    'platform', 'mobile', '1', '2',
                ]
            )
            raise ValueError(f'Неизвестное значение «{part}». Допустимые: {allowed}')
        if raw not in indices:
            indices.append(raw)
    props['usage_purpose_indices'] = indices
    props['usage_purpose_names'] = [
        USAGE_PURPOSE_DISPLAY.get(i, f'Неизвестное ({i})') for i in indices
    ]
    return ', '.join(USAGE_PURPOSE_DISPLAY.get(i, i) for i in indices)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_prop(source_dir, prop, value):
    """Set *prop* to *value* in Configuration.properties.json inside *source_dir*."""
    canonical = _normalize_property(prop)
    if canonical is None:
        known = 'main_launch_mode (ОсновнойРежимЗапуска), usage_purpose (НазначениеИспользования)'
        raise ValueError(f'Неизвестное свойство «{prop}». Поддерживаются: {known}')

    props = ensure_properties(source_dir)

    if canonical == 'main_launch_mode':
        display = _set_main_launch_mode(props, value)
    elif canonical == 'usage_purpose':
        display = _set_usage_purpose(props, value)

    _save_json(os.path.join(source_dir, PROPERTIES_FILE), props)
    print(f'[set_prop] Установлено: {canonical} = {display}')


def main():
    parser = argparse.ArgumentParser(
        description='Установить свойство конфигурации в Configuration.properties.json'
    )
    parser.add_argument(
        'source_dir',
        help='Папка с исходниками (содержит Configuration.properties.json / Configuration.json)',
    )
    parser.add_argument(
        'property',
        help='Имя свойства: main_launch_mode | ОсновнойРежимЗапуска | usage_purpose | НазначениеИспользования',
    )
    parser.add_argument(
        'value',
        help='Значение (см. SKILL.md)',
    )
    args = parser.parse_args()

    try:
        set_prop(args.source_dir, args.property, args.value)
    except (ValueError, FileNotFoundError) as e:
        print(f'Ошибка: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
