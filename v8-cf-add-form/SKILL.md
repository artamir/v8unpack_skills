---
name: v8-cf-add-form
user-invocable: true
description: >
  Добавление формы (Form) в справочник в JSON-исходниках распакованной конфигурации 1С.
  Копирует директорию формы из эталонного каталога и регистрирует её в Catalog.json и Configuration.json.
---

# v8-cf-add-form

## Описание

Скилл добавляет форму в справочник в исходниках распакованной конфигурации 1С (v8unpack-формат).

- Копирует `Catalog/<catalog_name>/CatalogForm/<form_name>/` из эталонного каталога
- Копирует `CatalogForm/v8unpack_include_order.json`
- Регистрирует форму в `Catalog.json` и `Configuration.json`

## Использование

- «добавь форму ФормаЭлемента в справочник Справочник01»
- «add form ФормаЭлемента to Справочник01 from ref_sources/step_0015»

## Скрипт

Файл: `tools/add_form.py`

```
python tools/add_form.py <source_dir> <catalog_name> <form_name> <ref_catalog_dir>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (`src/<Проект>`)
- `catalog_name` — имя папки справочника (например, `Справочник01`)
- `form_name` — имя добавляемой формы (например, `ФормаЭлемента`)
- `ref_catalog_dir` — эталонный каталог справочника с формой (например, `ref_sources/step_0015/Catalog/Справочник01`); родительская папка используется для поиска эталонного `Configuration.json`

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- Если справочник не найден: ответить «Ошибка: справочник <catalog_name> не найден в <source_dir>.»
- Если форма не найдена в эталонном каталоге: ответить «Ошибка: форма <form_name> не найдена в <ref_catalog_dir>.»

## Связанные скиллы

- v8-cf-remove-form — удаление формы из справочника
- v8-cf-add-catalog — добавление справочника
