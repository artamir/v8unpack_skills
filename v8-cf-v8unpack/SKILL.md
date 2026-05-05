---
name: v8-cf-v8unpack
description: >
  Распаковка .cf файла выгрузки конфигурации 1С с помощью v8unpack.exe.
  Может автоматически определять пути по проекту или принимать их явно параметрами.
  Пример: "распакуй NLTrade".
---
# cf-v8unpack

## Описание

**Важно:** Запускайте скрипты в соответствующей среде: файлы с расширением `.os` — только через `oscript`, файлы с расширением `.ps1` — только через PowerShell.

Скилл распаковывает .cf файл выгрузки конфигурации 1С в структуру исходников проекта, используя v8unpack.exe.

> **Важно:** Запускайте скрипты в соответствующей среде: файлы с расширением `.os` — только через `oscript`, файлы с расширением `.ps1` — только через PowerShell.
- При вызове только с именем проекта берёт cf и каталог назначения из v8.projects.json
- При необходимости принимает явные параметры: имя проекта, путь распаковки, путь к cf-файлу
- Запускает v8unpack.exe с нужными параметрами
- Контролирует результат и выводит ошибки

## Формы вызова
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8unpack/tools/cf-v8unpack.ps1 <ИмяПроекта>`
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8unpack/tools/cf-v8unpack.ps1 <ИмяПроекта> <ПутьНазначения> <ПутьКCf>`

## Примеры
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8unpack/tools/cf-v8unpack.ps1 NLTrade_invoice`
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8unpack/tools/cf-v8unpack.ps1 NLTrade_invoice temp/NLTrade_invoice/unpack temp/NLTrade_invoice/custom.cf`

## Использование

- "распакуй NLTrade"
- "распакуй cf для NLTrade"
- "распакуй нлтрейд"

## Пример вызова

  .github/skills/.tools/v8unpack.exe -E <cf-файл> <папка-исходников>

## Требования
- v8unpack.exe должен быть расположен по пути .github/skills/.tools/v8unpack.exe
- Файл v8.projects.ini должен быть корректно заполнен

## Связанные скиллы
- cf-v8pack — упаковка исходников обратно в cf
