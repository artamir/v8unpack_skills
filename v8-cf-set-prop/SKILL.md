---
name: v8-cf-set-prop
user-invocable: true
description: |
  Устанавливает свойство конфигурации 1С через файл Configuration.properties.json,
  который создаётся v8unpack при распаковке CF.
  Если файл отсутствует или не содержит нужное свойство, автоматически извлекает
  текущие значения из Configuration.json.
---

# v8-cf-set-prop

## Назначение

Скилл изменяет свойства конфигурации 1С в распакованных исходниках, работая
с файлом `Configuration.properties.json` — человекочитаемым представлением,
которое v8unpack формирует из `Configuration.json` при распаковке.

После изменения свойства файл `Configuration.properties.json` сохраняется, и
при следующей упаковке (v8pack / `v8-cf-v8pack`) v8unpack автоматически
применяет его к `Configuration.json`.

## Поддерживаемые свойства

| Имя свойства | Псевдонимы | Допустимые значения |
|---|---|---|
| `main_launch_mode` | `ОсновнойРежимЗапуска` | `УправляемоеПриложение` / `managed` / `1` |
| | | `ОбычноеПриложение` / `ordinary` / `0` |
| `usage_purpose` | `НазначениеИспользования` | `Приложение для платформы` / `platform` / `1` |
| | | `Приложение для мобильной платформы` / `mobile` / `2` |
| | | Через запятую — добавляет оба назначения |

## Алгоритм работы

1. Читает `Configuration.properties.json` из указанной папки.
2. Если файл не найден — создаёт его из `Configuration.json`.
3. Если нужное свойство отсутствует в файле (старый v8unpack) — дополняет его,
   читая текущее значение из `Configuration.json`.
4. Устанавливает запрошенное значение.
5. Сохраняет `Configuration.properties.json`.

При следующей упаковке v8unpack применит изменения к `Configuration.json`.

## Использование

```
python tools/set_prop.py <source_dir> <property> <value>
```

| Аргумент | Описание |
|---|---|
| `source_dir` | Папка с `Configuration.properties.json` / `Configuration.json` |
| `property` | Имя свойства (русское или английское) |
| `value` | Новое значение |

## Примеры

```bash
# Переключить в режим обычного приложения
python tools/set_prop.py src/MyConf main_launch_mode ОбычноеПриложение

# Переключить в управляемое приложение (коротко)
python tools/set_prop.py src/MyConf ОсновнойРежимЗапуска managed

# Назначение — только для платформы
python tools/set_prop.py src/MyConf usage_purpose "Приложение для платформы"

# Назначение — для платформы и мобильной платформы
python tools/set_prop.py src/MyConf НазначениеИспользования "Приложение для платформы, Приложение для мобильной платформы"
```

## Структура Configuration.properties.json

```json
{
  "schema": "v8unpack.configuration-properties.v1",
  "source": "Configuration.json",
  "raw_paths": {
    "main_launch_mode": "header[0][3][1][1][21]",
    "usage_purpose": "header[0][3][1][1][33]"
  },
  "main_launch_mode": "1",
  "usage_purpose_indices": ["1"],
  "usage_purpose_names": ["Приложение для платформы"]
}
```

## Расширение: добавление новых свойств

Если нужного свойства нет ни в `Configuration.properties.json`, ни в
`Configuration.json` по известному пути — необходимо доработать v8unpack:

1. **Добавить извлечение** в `_extract_configuration_properties()` в
   `vendor/v8unpack/src/v8unpack/decoder.py`:
   - Определить индекс нового свойства в массиве `header[0][3][1][1]`.
   - Добавить маппинг значений (числовой код → читаемое имя).
   - Записать в `properties[<новый_ключ>]`.

2. **Добавить применение** в `_apply_configuration_properties()` в том же файле:
   - Прочитать значение из `properties.get('<новый_ключ>')`.
   - Преобразовать при необходимости (имя → код).
   - Присвоить `params[<индекс>]`.

3. **Добавить поддержку** в `tools/set_prop.py`:
   - Расширить словари маппинга.
   - Добавить функцию `_set_<новое_свойство>()`.
   - Добавить ветку в `set_prop()`.

## Связанные скиллы

- `v8-cf-v8unpack` — распаковка CF в исходники (создаёт `Configuration.properties.json`)
- `v8-cf-v8pack` — упаковка исходников в CF (применяет `Configuration.properties.json`)
- `v8-cf-diff` — показ различий между версиями исходников
