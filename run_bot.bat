@echo off
chcp 65001 > nul
title Telegram AI & ACAT News Bot
cd /d %~dp0
echo ========================================================
echo  Starting Telegram AI & ACAT.KZ News Bot...
echo ========================================================
py -3.13 main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Trying fallback Python executable...
    C:\Users\d-kan\AppData\Local\Programs\Python\Python313\python.exe main.py
)
pause
