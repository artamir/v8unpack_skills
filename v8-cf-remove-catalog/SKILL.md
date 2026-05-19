---
name: v8-cf-remove-catalog
user-invocable: true
description: >
  Удаление справочника (Catalog) из JSON-исходников распакованной конфигурации 1С.
  Удаляет директорию справочника, обновляет include_order, Configuration.json и timestamps.
---

# v8-cf-remove-catalog

## Описание

Скилл удаляет справочник из исходников распакованной конфигурации 1С (v8unpack-формат).

- Удаляет `Catalog/<ИмяСправочника>/`
- Обновляет `Catalog/v8unpack_include_order.json` (удаляет UUID; удаляет файл, если список стал пустым)
- Удаляет `Catalog/`, если директория стала пустой
- Удаляет UUID справочника из `Configuration.json`
- Обновляет `.v8unpack_outer_timestamps.json` (удаляет UUID из `_file_order`, `_toc_order`, `_file_times`)

## Использование

- «удали справочник Справочник1»
- «remove catalog Справочник1 from project»

## Скрипт

Файл: `tools/remove_catalog.py`

```
python tools/remove_catalog.py <source_dir> <catalog_name>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (`src/<Проект>`)
- `catalog_name` — имя удаляемого справочника (например, `Справочник1`)

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- Если справочник не найден: ответить «Ошибка: справочник <catalog_name> не найден в <source_dir>.»

## Связанные скиллы

- v8-cf-add-catalog — добавление справочника
- v8-cf-v8pack — упаковка исходников обратно в CF
