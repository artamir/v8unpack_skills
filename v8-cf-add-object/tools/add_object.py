import argparse
import json
import os
import re
import uuid
from copy import deepcopy

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def gen_guid():
    return str(uuid.uuid4())


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_uuid_string(value):
    return isinstance(value, str) and UUID_RE.match(value) is not None


def remap_uuids(node, mapping):
    if isinstance(node, dict):
        return {k: remap_uuids(v, mapping) for k, v in node.items()}

    if isinstance(node, list):
        return [remap_uuids(v, mapping) for v in node]

    if is_uuid_string(node):
        if node == ZERO_UUID:
            return node
        if node not in mapping:
            mapping[node] = gen_guid()
        return mapping[node]

    return node


def find_templates(project_src_dir, object_type):
    target_file = f"{object_type}.json"
    candidates = []

    preferred_root = os.path.join(project_src_dir, object_type)
    if os.path.isdir(preferred_root):
        for root, _, files in os.walk(preferred_root):
            if target_file in files:
                candidates.append(os.path.join(root, target_file))

    for root, _, files in os.walk(project_src_dir):
        if target_file in files:
            path = os.path.join(root, target_file)
            if path not in candidates:
                candidates.append(path)

    return candidates


def apply_common_fields(data, name, name_ru, comment):
    data["name"] = name
    current_name2 = data.get("name2")
    if isinstance(current_name2, dict):
        current_name2["ru"] = name_ru
    else:
        data["name2"] = {"ru": name_ru}

    if comment is not None:
        data["comment"] = comment


def create_object(project_src_dir, object_type, name, name_ru, template=None, comment=None):
    if template:
        template_path = template
    else:
        candidates = find_templates(project_src_dir, object_type)
        if not candidates:
            raise RuntimeError(
                f"Template for '{object_type}' not found. Add --template or create at least one {object_type}.json"
            )
        template_path = candidates[0]

    data = load_json(template_path)
    data = deepcopy(data)

    uuid_mapping = {}
    data = remap_uuids(data, uuid_mapping)
    apply_common_fields(data, name, name_ru, comment)

    out_path = os.path.join(project_src_dir, object_type, name, f"{object_type}.json")
    if os.path.exists(out_path):
        raise RuntimeError(f"Object file already exists: {out_path}")

    save_json(out_path, data)
    return out_path, template_path, len(uuid_mapping)


def main():
    parser = argparse.ArgumentParser(
        description="Create a new 1C metadata object JSON from a template object of the same type"
    )
    parser.add_argument("--project-src", required=True, help="Path to project src folder, e.g. src/NLTrade")
    parser.add_argument("--type", required=True, help="Metadata object type, e.g. Constant, Catalog, Document, Enum")
    parser.add_argument("--name", required=True, help="Object name")
    parser.add_argument("--name-ru", required=True, help="Russian synonym")
    parser.add_argument("--template", help="Optional path to explicit template <Type>.json")
    parser.add_argument("--comment", help="Optional comment value")

    args = parser.parse_args()

    out_path, template_path, replaced = create_object(
        project_src_dir=args.project_src,
        object_type=args.type,
        name=args.name,
        name_ru=args.name_ru,
        template=args.template,
        comment=args.comment,
    )

    print(f"Template: {template_path}")
    print(f"UUID replaced: {replaced}")
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()
