---
name: v8-cf-remove-tabular-section
user-invocable: true
description: >
  Удаление табличной части (TabularSection) из справочника в JSON-исходниках распакованной конфигурации 1С.
  Удаляет запись ТЧ из Catalog.json и уменьшает счётчик табличных частей.
---

# v8-cf-remove-tabular-section

## Описание

Скилл удаляет табличную часть из справочника в исходниках распакованной конфигурации 1С (v8unpack-формат).

- Удаляет запись ТЧ из `header[0][5]` файла `Catalog.json`
- Уменьшает счётчик ТЧ в `header[0][5][1]`
- Перезаписывает `Catalog.tabular_sections.json`

## Использование

- «удали табличную часть ТабличнаяЧасть1 из справочника Справочник01»
- «remove tabular section ТабличнаяЧасть1 from Справочник01»

## Скрипт

Файл: `tools/remove_tabular_section.py`

```
python tools/remove_tabular_section.py <source_dir> <catalog_name> <ts_name>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (`src/<Проект>`)
- `catalog_name` — имя папки справочника (например, `Справочник01`)
- `ts_name` — имя удаляемой табличной части (например, `ТабличнаяЧасть1`)

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- Если справочник не найден: ответить «Ошибка: справочник <catalog_name> не найден в <source_dir>.»
- Если табличная часть не найдена: ответить «Ошибка: табличная часть <ts_name> не найдена в справочнике <catalog_name>.»

## Связанные скиллы

- v8-cf-add-tabular-section — добавление табличной части
- v8-cf-remove-tabsection-column — удаление колонки из ТЧ
