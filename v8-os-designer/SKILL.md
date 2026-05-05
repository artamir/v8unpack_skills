---
name: v8-os-designer
user-invocable: true
description: >
  Скилл для запуска конфигуратора 1С выбранного проекта через v8-runner.bat (vrunner), с автоматическим определением всех путей и параметров из v8.projects.ini.
---

# v8-os-designer

## Описание

Скилл позволяет открыть конфигуратор 1С для выбранного проекта, используя v8-runner.bat (vrunner) и автоматические параметры из v8.projects.ini.

- Определяет путь к базе из секции [project.<Имя>] → current
- По умолчанию использует логин из [project.<Имя>.logins.default] (db_user/db_pwd)
- Формирует команду для vrunner (через v8-runner.bat) для запуска конфигуратора
- Сообщает об ошибках, если база или логин не указаны

## Использование

- "открой конфигуратор NLTrade"
- "запусти конфигуратор для проекта <Имя>"

## Пример вызова

    .github/skills/.tools/oscript/v8-runner.bat designer --ibconnection "/F<путь_к_базе>" --db-user <db_user> --db-pwd <db_pwd>

## Требования
- v8-runner.bat, ovm.exe и vrunner должны быть зарегистрированы в секции [tools] v8.projects.ini
- В секции [project.<Имя>] должен быть указан параметр current

## Связанные скиллы
- v8-os-vrunner — универсальный запуск vrunner
