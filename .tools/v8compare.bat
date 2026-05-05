@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem Скрипт сравнения конфигурации базы 1С и файла *.cf (полный режим)
rem Вывод отчёта сохраняется в текстовый файл
rem ============================================================

rem ---------- НАСТРОЙКИ (укажите свои значения) ----------
rem Путь к 1cv8.exe (укажите актуальный путь к вашей платформе)
set P1CEXE=C:\Program Files (x86)\1cv8\8.3.21.1895\bin\1cv8.exe

rem Параметры подключения к базе:
rem   файловая     - /F"путь_к_базе"
set BASE=e:\1CBases\NL\NL_v8unpack\current\NLTrade_invoice\NLTrade_invoice_ib

set USER=Administrator
set PASS=P@rol@321

set CF=e:\1CBases\NL\NL_v8unpack\build\NLTrade_invoice\NLTrade_invoice.cf

set OUT=e:\1CBases\NL\NL_v8unpack\temp\NLTrade_invoice\diff_report_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt
rem (имя файла содержит дату/время, можно заменить на простой путь)
rem ---------- КОНЕЦ НАСТРОЕК ----------

echo Проверка наличия платформы 1С...
echo [DEBUG] Значение переменной P1CEXE: [%P1CEXE%]
set
echo [DEBUG] Строка запуска:
echo Проверка наличия файла CF...
echo Запуск сравнения конфигураций в режиме "Полный"...
echo ================================================
echo [DEBUG] Перед запуском 1cv8.exe
"%P1CEXE%" DESIGNER /F"%BASE%" /N"%USER%" /P"%PASS%" /CompareCfg -Full "%CF%" > "%OUT%"