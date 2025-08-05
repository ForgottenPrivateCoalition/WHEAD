@echo off
chcp 65001 >nul

:: Проверка прав администратора
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Admin rights required. Restarting as admin...
    powershell -Command "Start-Process -Verb runAs -FilePath '%~f0'"
    exit /b
)

:main_loop
cls
echo ┌─────┐ ┌─────┐ ┌─────┐  ┌───────────────────────────────────────────────────┐
echo │ ┌───┘ │ ┌─┐ │ │ ┌───┘  │ Forgotten Private Coalition                       │
echo │ └───┐ │ └─┘ │ │ │      │ Fake WHEA error trigger                           │
echo │ ┌───┘ │ ┌───┘ │ │      │ Private version                                   │
echo │ │     │ │     │ └───┐  │ License CC BY 4.0                                 │
echo └─┘     └─┘     └─────┘  └───────────────────────────────────────────────────┘
echo.
echo Available WHEA EventIDs and meanings:
echo  17 - General hardware error event
echo  18 - Machine Check Exception (MCE)
echo  19 - Corrected Machine Check error
echo  20 - PCI Express error
echo  41 - Detailed WHEA error report
echo  45 - Corrected memory error
echo  46 - Corrected processor error
echo  47 - Corrected PCI Express error
echo.
echo Команды:
echo  ex - Закрыть программу
echo  el - Открыть журнал событий Windows/System
echo  ec - Очистить все ошибки от источника TestWHEA
echo.

if defined last_message (
    echo %last_message%
    echo.
    set "last_message="
)

set /p input=Введите "EventID Level" (Level: 1=Warning, 2=Error) или команду (ex, el, ec): 

:: Проверка команд
if /i "%input%"=="ex" (
    exit /b
)
if /i "%input%"=="el" (
    start eventvwr.msc /s:"System"
    set last_message=Журнал событий Windows/System запущен.
    goto main_loop
)
if /i "%input%"=="ec" (
    echo Очистка всех ошибок от источника TestWHEA...
    wevtutil.exe cl System
    set last_message=Журнал System очищен.
    goto main_loop
)

:: Обработка ввода EventID и Level
for /f "tokens=1,2" %%a in ("%input%") do (
    set "code=%%a"
    set "level=%%b"
)

if not defined code (
    set last_message=Неверный ввод. Попробуйте снова.
    goto main_loop
)
if not defined level (
    set last_message=Неверный ввод. Попробуйте снова.
    goto main_loop
)

set executed=0

for %%E in (17 18 19 20 41 45 46 47) do (
    if "%code%"=="%%E" (
        if "%level%"=="1" (
            eventcreate /T WARNING /ID %%E /L SYSTEM /SO TestWHEA /D "Test warning WHEA (EventID %%E)"
            set executed=1
        ) else if "%level%"=="2" (
            eventcreate /T ERROR /ID %%E /L SYSTEM /SO TestWHEA /D "Test error WHEA (EventID %%E)"
            set executed=1
        )
    )
)

if "%executed%"=="1" (
    set last_message=Операция выполнена успешно.
    goto main_loop
) else (
    set last_message=Неверный ввод или неподдерживаемый EventID/Level. Попробуйте снова.
    goto main_loop
)
