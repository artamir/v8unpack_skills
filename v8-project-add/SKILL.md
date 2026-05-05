---
name: v8-project-add
description: >
  Добавление нового проекта 1С v8 в workspace. Создаёт папки src, temp, build
  для проекта и добавляет данные в v8.projects.json. В объекте проекта обязательно добавляются параметры db_user и db_pwd для поддержки авторизации при выгрузке cf. Используй когда нужно:
  создать новый проект, добавить проект, зарегистрировать базу, new project,
  add project, создай проект, добавь проект.
argument-hint: '<ИмяПроекта> [BaseDir]'
---

# add-project

**Важно:** Запускайте скрипты в соответствующей среде: файлы с расширением `.os` — только через `oscript`, файлы с расширением `.ps1` — только через PowerShell.

Этот скилл регистрирует новый проект 1С v8 в workspace: создаёт нужные папки
и добавляет объект проекта в `v8.projects.json`.
В объекте проекта обязательно добавляются параметры db_user и db_pwd (логин и пароль пользователя базы 1С, если требуется авторизация для операций с cf).

## Когда использовать

- Пользователь говорит: «создай проект X», «добавь новый проект X», «зарегистрируй базу X»
- Нужно добавить ещё один проект в уже настроенный workspace

Ключевые слова: `новый проект`, `добавить проект`, `создать проект`, `add project`, `new project`, `зарегистрировать`.

temp\<Имя>\          ← временные файлы
## Формат v8.projects.json

```json
{
  "tools": {
    "v8unpack": "...",
    "v8-runner": "...",
    "ovm": "..."
  },
  "projects": {
    "<Имя>": {
      "src": "src/<Имя>",
      "build": "build/<Имя>",
      "temp": "temp/<Имя>",
      "current": "current/<Имя>/<Имя>_ib",
      "current_cf": "current/<Имя>/cf",
      "logins": {
        "default": {
          "db_user": "...",
          "db_pwd": "..."
        }
      }
    }
  }
}
```

### Распаковка внешних форм (extforms)

Если в базе (`BASE_DIR`) есть файл `extforms\prnforms\Накладная.erf`, он
распакуется в `src\<Имя>\extforms\extforms\prnforms\Накладная\`.

Путь в `extforms` = относительный путь файла от `BASE_DIR` без расширения.
Промежуточные подпапки создаются автоматически.

## Что делает скрипт add-project.ps1

1. Проверяет отсутствие секции `[project.<Имя>]` в `v8.projects.ini`
2. Создаёт папки (если не существуют):
   - `current\<Имя>\<Имя>_ib\`
   - `src\<Имя>\cf\`
   - `src\<Имя>\extforms\`
   - `temp\<Имя>\`
   - `build\<Имя>\`
3. Добавляет секцию в конец `v8.projects.ini`
4. Сообщает, что нужно скопировать базу в `current\<Имя>\<Имя>_ib\`

## Порядок действий агента

1. Выяснить у пользователя **имя проекта** (латиница или кириллица, без пробелов).
2. Выяснить **путь к существующей базе данных 1С** (BASE_DIR) — или подтвердить, что база ещё не подключена.
3. Запустить скрипт добавления проекта:

```powershell
# Минимум — только имя (BASE_DIR = current\<Project>\<Project>_ib)
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта>

# С указанием существующей базы
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта> -BaseDir "E:\1CBases\<ИмяПроекта>\<ИмяПроекта>_ib"

# Перезаписать секцию если уже существует
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта> -Force
```

4. Показать пользователю вывод скрипта и получившуюся секцию в `v8.projects.ini`.
5. Если BASE_DIR пуст — напомнить скопировать туда файлы базы 1С.
6. После того как база скопирована, предложить распаковать метаданные и внешние формы:

```powershell
# Распаковать 1cv7.md -> src\<Project>\cf\
.\v7.ps1 -Project <ИмяПроекта> -Action unpack

# Распаковать все .ert/.rpt -> src\<Project>\extforms\
.\v7.ps1 -Project <ИмяПроекта> -Action unpack-extforms
```


## Результат

- Папки проекта созданы в workspace
- В `v8.projects.ini` появилась секция:
  ```ini
  [project.<Имя>]
  BASE_DIR=current\<Имя>\<Имя>_ib
  SRC_DIR=src\<Имя>\cf
  EXTFORMS_DIR=src\<Имя>\extforms
  TEMP_DIR=temp\<Имя>
  OUT_MD_FILE=build\<Имя>\1cv77.md
  ```
- Проект доступен для всех действий `v7.ps1`:
  `unpack`, `pack`, `open`, `syntax`, `unpack-extforms`


## Когда использовать

- Пользователь говорит: «создай проект X», «добавь новый проект X», «зарегистрируй базу X»
- Нужно добавить ещё один проект в уже настроенный workspace

Ключевые слова: `новый проект`, `добавить проект`, `создать проект`, `add project`, `new project`, `зарегистрировать`.

## Что делает скрипт

1. Проверяет, что в `v8.projects.ini` ещё нет секции `[project.<Имя>]`
2. Создаёт папки (если не существуют):
   - `src\<Имя>\cf` — для исходников метаданных
   - `temp\<Имя>` — для временных файлов
   - `build\<Имя>` — для результата сборки MD
   - `current\<Имя>` — для базы данных (только если `BaseDir` не задан)
3. Добавляет секцию в конец `v8.projects.ini`
4. Сообщает пользователю, если BASE_DIR ещё пуст и нужно скопировать базу

## Порядок действий агента

1. Выяснить у пользователя **имя проекта** (латиница или кириллица, без пробелов).
2. Выяснить **путь к существующей базе данных 1С** (BASE_DIR) — или подтвердить, что база ещё не подключена.
3. Запустить скрипт:

```powershell
# Минимум — только имя (BASE_DIR = current\<Project>)
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта>

# С указанием существующей базы
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта> -BaseDir "E:\1CBases\<ИмяПроекта>\<ИмяПроекта>_ib"

# Перезаписать секцию если уже существует
powershell -ExecutionPolicy Bypass -File .\.github\skills\add-project\scripts\add-project.ps1 -Project <ИмяПроекта> -Force
```

4. Показать пользователю вывод скрипта и получившуюся секцию в `v8.projects.ini`.
5. Если BASE_DIR пуст — напомнить скопировать туда файлы базы 1С.

## Результат

- Папки `src\<Имя>`, `temp\<Имя>`, `build\<Имя>` созданы в workspace
- В `v8.projects.ini` появилась секция:
  ```ini
  [project.<Имя>]
  BASE_DIR=current\<Имя>
  SRC_DIR=src\<Имя>
  TEMP_DIR=temp\<Имя>
  OUT_MD_FILE=build\<Имя>\1cv77.md
  ```
- Проект доступен для `.\v7.ps1 -Project <Имя> -Action unpack|pack|open|syntax`
