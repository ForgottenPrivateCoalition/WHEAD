@echo off
chcp 65001 >nul

:main
cls
echo ┌─────┐ ┌─────┐ ┌─────┐  ┌───────────────────────────────────────────────────┐
echo │ ┌───┘ │ ┌─┐ │ │ ┌───┘  │ Forgotten Private Coalition                       │
echo │ └───┐ │ └─┘ │ │ │      │ Python Bacth Starter                              │
echo │ ┌───┘ │ ┌───┘ │ │      │ Private version                                   │
echo │ │     │ │     │ └───┐  │ License CC BY 4.0                                 │
echo └─┘     └─┘     └─────┘  └───────────────────────────────────────────────────┘
echo Starting python project...
echo Python WHEA.py
echo.
python whea.py
pause
goto main