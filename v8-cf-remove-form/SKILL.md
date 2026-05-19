---
name: v8-cf-remove-form
user-invocable: true
description: >
  Удаление формы (Form) из справочника в JSON-исходниках распакованной конфигурации 1С.
  Удаляет директорию формы и обновляет Catalog.json.
---

# v8-cf-remove-form

## Описание

Скилл удаляет форму из справочника в исходниках распакованной конфигурации 1С (v8unpack-формат).

- Обновляет `Catalog.json header[0][7]`: уменьшает счётчик форм и удаляет UUID
- Обнуляет слот UUID формы в `Catalog.json header[0][1]`
- Удаляет директорию `CatalogForm/<ИмяФормы>/`
- Удаляет `CatalogForm/v8unpack_include_order.json`
- Удаляет `CatalogForm/`, если директория стала пустой

## Использование

- «удали форму ФормаЭлемента из справочника Справочник01»
- «remove form ФормаЭлемента from Справочник01»

## Скрипт

Файл: `tools/remove_form.py`

```
python tools/remove_form.py <source_dir> <catalog_name> <form_name>
```

Аргументы:
- `source_dir` — путь к распакованным исходникам проекта (`src/<Проект>`)
- `catalog_name` — имя папки справочника (например, `Справочник01`)
- `form_name` — имя удаляемой формы (например, `ФормаЭлемента`)

## Определение source_dir

Путь к исходникам берётся из `v8.projects.json`:

- Топ-уровневый проект (например, `BAU`): `projects.BAU.src` = `src/BAU`
- Подпроект (например, `BAU_KlientBank`): `projects.BAU.projects.BAU_KlientBank.src` = `src/BAU/BAU_KlientBank`

## Требования

- Исходники должны быть предварительно распакованы через v8unpack
- Если справочник не найден: ответить «Ошибка: справочник <catalog_name> не найден в <source_dir>.»
- Если форма не найдена: ответить «Ошибка: форма <form_name> не найдена в справочнике <catalog_name>.»

## Связанные скиллы

- v8-cf-add-form — добавление формы в справочник
- v8-cf-remove-catalog — удаление справочника
