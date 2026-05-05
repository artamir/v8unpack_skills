---
name: v8-project-delete
description: >
  Удаление проекта 1С v8 из workspace. Удаляет запись проекта из v8.projects.json
   и по умолчанию удаляет папки src, build, temp, current проекта. Используй когда нужно:
  удалить проект, убрать проект, remove project, delete project, удали проект,
  убери проект, снять проект.
argument-hint: '<ИмяПроекта> [--keep-folders]'
---

# v8-project-delete

**Важно:** Операция **необратима**. Перед удалением папок убедитесь, что данные не нужны или есть резервная копия.

Этот скилл удаляет проект из `v8.projects.json` и по умолчанию удаляет все папки проекта (`src`, `build`, `temp`, `current`).

## Когда использовать

- Пользователь говорит: «удали проект X», «убери проект X», «remove project X», «delete project X»
- Нужно очистить workspace от устаревшего или ненужного проекта

Ключевые слова: `удалить проект`, `убрать проект`, `удали проект`, `remove project`, `delete project`.

## Порядок действий агента

1. Выяснить у пользователя **имя проекта** (должен совпадать с ключом в `v8.projects.json`).
2. Уточнить: нужно ли **сохранять папки** (`src/<Имя>`, `build/<Имя>`, `temp/<Имя>`, `current/<Имя>`).
   - По умолчанию папки удаляются вместе с записью проекта.
   - Для сохранения папок использовать флаг `-KeepFolders`.
3. Запустить скрипт:

```powershell
# Удалить запись и папки проекта (режим по умолчанию)
powershell -ExecutionPolicy Bypass -File .\.github\skills\v8-project-delete\scripts\remove-project.ps1 -Project <ИмяПроекта>

# Удалить запись, но сохранить папки проекта
powershell -ExecutionPolicy Bypass -File .\.github\skills\v8-project-delete\scripts\remove-project.ps1 -Project <ИмяПроекта> -KeepFolders

# Без интерактивного подтверждения (например, в CI)
powershell -ExecutionPolicy Bypass -File .\.github\skills\v8-project-delete\scripts\remove-project.ps1 -Project <ИмяПроекта> -Force
```

4. Показать пользователю вывод скрипта.
5. Если использован `-KeepFolders` — сообщить, что папки остались на диске.

## Что делает скрипт

1. Проверяет наличие проекта в `v8.projects.json`
2. Запрашивает подтверждение (если не указан `-Force`)
3. Если **не** указан `-KeepFolders`:
   - Удаляет `src/<Имя>`, `build/<Имя>`, `temp/<Имя>`, `current/<Имя>`
4. Удаляет ключ проекта из секции `projects` в `v8.projects.json`
5. Сохраняет `v8.projects.json`

## Результат

- Запись проекта удалена из `v8.projects.json`
- Папки удалены по умолчанию (или сохранены при `-KeepFolders`)
- Проект недоступен для дальнейших операций v8-runner / v8unpack
