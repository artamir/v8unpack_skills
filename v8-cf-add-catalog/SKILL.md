---
name: v8-cf-add-catalog
user-invocable: true
description: >
  Добавление нового справочника (Catalog) в JSON-исходники распакованной конфигурации 1С.
  Копирует файлы определения справочника в целевую директорию и регистрирует его в Configuration.json.
---

# v8-cf-add-catalog

## Описание

Скилл добавляет новый справочник в исходники распакованной конфигурации 1С (v8unpack-формат).

- Создаёт `Catalog/<ИмяСправочника>/Catalog.json` и `Catalog.id.json` из указанного источника данных
- Обновляет `Catalog/v8unpack_include_order.json`
- Регистрирует UUID справочника в `Configuration.json` (список справочников)
- Обновляет `.v8unpack_outer_timestamps.json` для корректной упаковки CF

## Использование

- «добавь справочник Справочник1 в проект NLTrade»
- «add catalog Контрагенты из ref_sources/step_0006»

## Скрипт

Файл: `tools/add_catalog.py`

```
python tools/add_catalog.py <source_dir> <catalog_name> <catalog_data_dir>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (папка `src/<Проект>`)
- `catalog_name` — имя справочника (например, `Справочник1`)
- `catalog_data_dir` — папка с `Catalog.json` и `Catalog.id.json` для добавляемого справочника

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- `catalog_data_dir` должен содержать корректные `Catalog.json` и `Catalog.id.json`
- Если `source_dir` не найден: ответить «Ошибка: директория исходников не найдена по пути <source_dir>.»
- Если `catalog_data_dir` не содержит нужных файлов: ответить «Ошибка: в <catalog_data_dir> не найден Catalog.json или Catalog.id.json.»

## Связанные скиллы

- v8-cf-add-object — добавление объектов других типов
- v8-cf-remove-catalog — удаление справочника
- v8-cf-v8pack — упаковка исходников обратно в CF
