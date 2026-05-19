---
name: v8-cf-add-attribute
user-invocable: true
description: >
  Добавление нового реквизита (Attribute) в справочник в JSON-исходниках распакованной конфигурации 1С.
  Читает определение реквизита из эталонного каталога и вставляет его в Catalog.json целевого справочника.
---

# v8-cf-add-attribute

## Описание

Скилл добавляет реквизит в справочник в исходниках распакованной конфигурации 1С (v8unpack-формат).

- Добавляет запись реквизита в `header[0][6]` файла `Catalog.json`
- Увеличивает счётчик реквизитов в `header[0][6][1]`
- Читает определение реквизита из эталонного каталога справочника

## Использование

- «добавь реквизит ТестРеквизитСтрока50 в справочник Справочник01»
- «add attribute ТестРеквизитЧисло10 to Справочник01 from ref_sources/step_0010»

## Скрипт

Файл: `tools/add_attribute.py`

```
python tools/add_attribute.py <source_dir> <catalog_name> <attr_name> <attr_source_catalog_dir>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (`src/<Проект>`)
- `catalog_name` — имя папки справочника (например, `Справочник01`)
- `attr_name` — имя добавляемого реквизита (например, `ТестРеквизитСтрока50`)
- `attr_source_catalog_dir` — папка с эталонным `Catalog.json` (например, `ref_sources/step_0010/Catalog/Справочник01`)

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- Если справочник не найден: ответить «Ошибка: справочник <catalog_name> не найден в <source_dir>.»
- Если реквизит не найден в эталонном каталоге: ответить «Ошибка: реквизит <attr_name> не найден в <attr_source_catalog_dir>.»

## Связанные скиллы

- v8-cf-remove-attribute — удаление реквизита из справочника
- v8-cf-add-catalog — добавление справочника
- v8-cf-add-tabsection-column — добавление колонки в табличную часть
