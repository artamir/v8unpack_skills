@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set P1C=C:\Program Files (x86)\1cv8\8.3.21.1895\bin\1cv8.exe
set BASE=e:\1CBases\NL\NL_v8unpack\current\NLTrade_invoice\NLTrade_invoice_ib
set USER=Administrator
set PASS=P@rol@321
set CF=e:\1CBases\NL\NL_v8unpack\build\NLTrade_invoice\NLTrade_invoice.cf
set OUT=e:\1CBases\NL\NL_v8unpack\temp\NLTrade_invoice\diff_report.txt

echo P1C: %P1C%
echo BASE: %BASE%
echo USER: %USER%
echo PASS: %PASS%
echo CF: %CF%
echo OUT: %OUT%

echo Проверка наличия платформы 1С...
if not exist "%P1C%" (
    echo [ОШИБКА] Платформа не найдена по пути: %P1C%
    pause
    exit /b 1
)

echo Проверка наличия файла CF...
if not exist "%CF%" (
    echo [ОШИБКА] Файл конфигурации не найден: %CF%
    pause
    exit /b 2
)

echo Запуск сравнения конфигураций...
echo Команда:
echo "%P1C%" DESIGNER /F"%BASE%" /N"%USER%" /P"%PASS%" /CompareCfg -Full "%CF%" ^> "%OUT%"

pause
