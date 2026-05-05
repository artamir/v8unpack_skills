---
name: v8-cf-v8pack
description: >
  Упаковка исходников проекта 1С обратно в .cf файл с помощью v8unpack.exe.
  Может автоматически определять пути по проекту или принимать их явно параметрами.
  Пример: "запакуй NLTrade".
---

# v8-cf-v8pack

## Описание
**Важно:** Запускайте скрипты в соответствующей среде: файлы с расширением `.os` — только через `oscript`, файлы с расширением `.ps1` — только через PowerShell.

Скилл собирает .cf файл из исходников проекта, используя v8unpack.exe.

- При вызове только с именем проекта берёт путь к исходникам и cf-файлу из v8.projects.json
- При необходимости принимает явные параметры: имя проекта, путь к исходникам, путь к cf-файлу
- Запускает v8unpack.exe с нужными параметрами
- Контролирует результат и выводит ошибки

## Формы вызова
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8pack/tools/cf-v8pack.ps1 <ИмяПроекта>`
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8pack/tools/cf-v8pack.ps1 <ИмяПроекта> <ПутьКИсходникам> <ПутьКCf>`

## Примеры
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8pack/tools/cf-v8pack.ps1 NLTrade_invoice`
- `powershell -ExecutionPolicy Bypass -File .github/skills/v8-cf-v8pack/tools/cf-v8pack.ps1 NLTrade_invoice src/NLTrade_invoice temp/NLTrade_invoice/custom.cf`

## Использование

- "запакуй NLTrade"
- "упакуй cf для NLTrade"
- "запакуй нлтрейд"

## Пример вызова

  .github/skills/.tools/v8unpack.exe -B <папка-исходников> <cf-файл>

## Требования
- v8unpack.exe должен быть расположен по пути .github/skills/.tools/v8unpack.exe
- Файл v8.projects.ini должен быть корректно заполнен
- Перед запаковкой исходников в cf обязательно удалять файл dummy.zip (если присутствует).

## Связанные скиллы
- v8-cf-v8unpack — распаковка cf в исходники
