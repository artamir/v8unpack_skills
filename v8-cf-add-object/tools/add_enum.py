import json
import os
import re
import sys
import uuid
from copy import deepcopy

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ZERO_UUID = "00000000-0000-0000-0000-000000000000"
ENUM_TYPE_GUID = "f6a80749-5ad7-400b-8519-39dc5dff2542"

# Эти ключи секций в header Enum должны оставаться фиксированными,
# иначе объект может не попасть в итоговый состав конфигурации.
ENUM_HEADER_SECTION_GUIDS = {
    "33f2e54b-37ce-4a7a-a569-b648d7aa4634",
    "3daea016-69b7-4ed4-9453-127911372fe6",
    "6d8d73a7-ba29-401d-9032-3872ec2d6433",
    "bee0a08c-07eb-40c0-8544-5c364c171465",
}


def gen_guid():
    return str(uuid.uuid4())


def is_uuid(value):
    return isinstance(value, str) and UUID_RE.match(value) is not None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def quote_string(value):
    return f'"{value}"'


def remap_uuids(node, mapping):
    if isinstance(node, dict):
        return {k: remap_uuids(v, mapping) for k, v in node.items()}
    if isinstance(node, list):
        return [remap_uuids(v, mapping) for v in node]
    if is_uuid(node):
        if node == ZERO_UUID or node in ENUM_HEADER_SECTION_GUIDS:
            return node
        if node not in mapping:
            mapping[node] = gen_guid()
        return mapping[node]
    return node


def iter_enum_templates(enum_dir=None):
    search_roots = []
    if enum_dir:
        search_roots.append(enum_dir)
    search_roots.append("src")

    seen = set()
    for root in search_roots:
        if not root or root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for current_root, _, files in os.walk(root):
            if "Enum.json" in files:
                yield os.path.join(current_root, "Enum.json")


def load_enum_template(enum_dir=None):
    for template_path in iter_enum_templates(enum_dir):
        template = load_json(template_path)
        if not template.get("header") or not isinstance(template["header"], list):
            continue
        if not template["header"] or not isinstance(template["header"][0], list):
            continue
        top = template["header"][0]
        if len(top) < 6 or not isinstance(top[1], list):
            continue
        value_block = top[-1]
        if not isinstance(value_block, list) or len(value_block) < 3:
            continue
        print(f"[DEBUG] Используется шаблон перечисления: {template_path}")
        return deepcopy(template)
    raise RuntimeError("Не найден шаблон Enum.json для создания перечисления")


def update_enum_names(enum_data, name, name_ru):
    enum_data["name"] = name
    enum_data["name2"] = {"ru": name_ru}
    enum_data["comment"] = ""

    top = enum_data["header"][0]
    meta = top[1]

    if len(meta) > 5 and isinstance(meta[5], list) and len(meta[5]) > 1 and isinstance(meta[5][1], list):
        title_node = meta[5][1]
        if len(title_node) > 2:
            title_node[2] = quote_string(name)
        if len(title_node) > 3:
            title_node[3] = ["1", '"ru"', quote_string(name_ru)]
        if len(title_node) > 4:
            title_node[4] = '""'


def rebuild_values(enum_data, values):
    if not values:
        raise ValueError("Для нового перечисления нужно передать хотя бы одно значение")

    top = enum_data["header"][0]
    meta = top[1]
    value_block = top[-1]

    if not isinstance(value_block, list) or len(value_block) < 3:
        raise RuntimeError("Некорректная структура value block в Enum.json")

    entry_template = deepcopy(value_block[2])

    new_entries = []
    for value_name in values:
        entry = deepcopy(entry_template)
        entry[0][0] = "0"
        entry[0][1][1][2] = gen_guid()
        entry[0][1][2] = quote_string(value_name)
        entry[0][1][3] = ["1", '"ru"', quote_string(value_name)]
        entry[0][1][4] = '""'
        new_entries.append(entry)

    value_block[1] = str(len(values))
    value_block[2:] = new_entries


def create_enum(enum_dir, name, name_ru, values):
    enum_data = load_enum_template(enum_dir)

    uuid_mapping = {}
    enum_data = remap_uuids(enum_data, uuid_mapping)

    update_enum_names(enum_data, name, name_ru)
    rebuild_values(enum_data, values)

    return enum_data


def walk_lists(node):
    if isinstance(node, list):
        yield node
        for item in node:
            yield from walk_lists(item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from walk_lists(value)


def register_enum_in_configuration(project_src_dir, enum_uuid):
    config_path = os.path.join(project_src_dir, "Configuration.json")
    if not os.path.exists(config_path):
        raise RuntimeError(f"Не найден файл Configuration.json: {config_path}")

    data = load_json(config_path)

    enum_block = None
    for node in walk_lists(data):
        if len(node) >= 2 and node[0] == ENUM_TYPE_GUID and isinstance(node[1], str) and node[1].isdigit():
            enum_block = node
            break

    if enum_block is None:
        raise RuntimeError("Не найден блок перечислений в Configuration.json")

    changed = False
    if enum_uuid not in enum_block[2:]:
        enum_block.append(enum_uuid)
        enum_block[1] = str(int(enum_block[1]) + 1)
        changed = True

    quoted_uuid = quote_string(enum_uuid)
    versions = data.get("versions")
    if isinstance(versions, list) and versions and isinstance(versions[0], list):
        version_row = versions[0]
        if quoted_uuid not in version_row:
            version_row.extend([quoted_uuid, gen_guid()])
            if len(version_row) > 1 and isinstance(version_row[1], str) and version_row[1].isdigit():
                version_row[1] = str(int(version_row[1]) + 1)
            changed = True

    if changed:
        save_json(config_path, data)

    return config_path, changed


def add_value(enum_path, value_name):
    data = load_json(enum_path)
    top = data["header"][0]
    meta = top[1]
    value_block = top[-1]

    entry = deepcopy(value_block[2])
    entry[0][0] = "0"
    entry[0][1][1][2] = gen_guid()
    entry[0][1][2] = quote_string(value_name)
    entry[0][1][3] = ["1", '"ru"', quote_string(value_name)]
    entry[0][1][4] = '""'

    value_block.append(entry)
    value_block[1] = str(int(value_block[1]) + 1)

    save_json(enum_path, data)
    print(f"Значение {value_name} добавлено в {enum_path}")


def parse_option(argv, key, default=None):
    if key in argv:
        idx = argv.index(key)
        if idx + 1 >= len(argv):
            raise ValueError(f"Для параметра {key} не задано значение")
        value = argv[idx + 1]
        del argv[idx:idx + 2]
        return value
    return default


def main():
    argv = sys.argv[1:]
    if not argv:
        print("Использование: python add_enum.py new <Имя> <РусскоеИмя> <Знач1> [<Знач2> ...] [--project-src <Путь>] [--enum-dir <Путь>] | add <ПутьКEnum.json> <НовоеЗначение>")
        return

    cmd = argv[0]

    if cmd == "new":
        argv = argv[1:]
        project_src_dir = parse_option(argv, "--project-src", "src/NLTrade_invoice")
        enum_dir = parse_option(argv, "--enum-dir", os.path.join(project_src_dir, "Enum"))

        if len(argv) < 3:
            raise ValueError("Недостаточно аргументов для new")

        name = argv[0]
        name_ru = argv[1]
        values = argv[2:]

        enum_data = create_enum(enum_dir, name, name_ru, values)
        enum_uuid = gen_guid()

        out_dir = os.path.join(enum_dir, name)
        os.makedirs(out_dir, exist_ok=True)

        enum_json_path = os.path.join(out_dir, "Enum.json")
        enum_id_path = os.path.join(out_dir, "Enum.id.json")

        save_json(enum_json_path, enum_data)
        save_json(enum_id_path, {"uuid": enum_uuid})

        config_path, config_changed = register_enum_in_configuration(project_src_dir, enum_uuid)

        print(f"Создано перечисление {name} в {enum_json_path}")
        print(f"Создан файл идентификатора {enum_id_path}")
        print(f"Configuration обновлен: {config_path} (изменен={config_changed})")

    elif cmd == "add":
        if len(argv) < 3:
            raise ValueError("Использование: python add_enum.py add <ПутьКEnum.json> <НовоеЗначение>")
        enum_path = argv[1]
        value_name = argv[2]
        add_value(enum_path, value_name)

    else:
        raise ValueError("Неизвестная команда")


if __name__ == "__main__":
    main()
