import os
import sys
import subprocess
from datetime import datetime
import json

if len(sys.argv) < 2:
    print("Не указано имя проекта. Пример: python tools/v8-cf-diff-wrapper.py NLTrade_invoice")
    sys.exit(1)

project = sys.argv[1]
date_suffix = datetime.now().strftime('%Y%m%d_%H%M%S')

with open("v8.projects.json", encoding="utf-8-sig") as f:
    cfg = json.load(f)

project_cfg = cfg["projects"].get(project)
if not project_cfg:
    print(f"Проект не найден в v8.projects.json: {project}")
    sys.exit(1)

source_dir = os.path.join("src", project)
temp_root = project_cfg.get("temp", os.path.join("temp", project))
cf_temp_path = os.path.join(temp_root, f"{project}_{date_suffix}.cf")
temp_unpack_dir = os.path.join(temp_root, f"{project}_{date_suffix}")

os.makedirs(temp_root, exist_ok=True)

# 1. Упаковка исходников через PowerShell-скрипт
print("[1/4] Упаковка исходников...")
res = subprocess.run([
    "powershell",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    ".github/skills/v8-cf-v8pack/tools/cf-v8pack.ps1",
    project,
    source_dir,
    cf_temp_path,
])
if res.returncode != 0 or not os.path.exists(cf_temp_path):
    print(f"Не удалось создать cf-файл: {cf_temp_path}")
    sys.exit(1)

# 2. Подготовка временной папки распаковки
print("[2/4] Подготовка временной папки...")
if os.path.exists(temp_unpack_dir):
    import shutil
    shutil.rmtree(temp_unpack_dir)

# 3. Распаковка cf во временную папку через PowerShell-скрипт
print("[3/4] Распаковка cf-файла...")
res = subprocess.run([
    "powershell",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    ".github/skills/v8-cf-v8unpack/tools/cf-v8unpack.ps1",
    project,
    temp_unpack_dir,
    cf_temp_path,
])
if res.returncode != 0 or not os.path.exists(temp_unpack_dir) or not os.listdir(temp_unpack_dir):
    print(f"Не удалось распаковать cf-файл: {temp_unpack_dir}")
    sys.exit(1)

# 4. Сравнение исходников и распакованной папки
print("[4/4] Сравнение исходников и распакованной папки...")
res = subprocess.run(["python", "tools/v8_src_comparer/v8_src_comparer.py", source_dir, temp_unpack_dir])

print("Проверка завершена. См. результат сравнения.")
