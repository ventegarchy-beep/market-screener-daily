@echo off
title Stock Screener v3

echo.
echo  =========================================
echo   MARKET SCREENER v3
echo   S&P500 - NASDAQ100 - CAC40
echo  =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR : Python non installe.
    echo  Telechargez-le sur https://www.python.org
    pause & exit /b
)

echo  Installation des dependances...
pip install yfinance pandas numpy requests lxml --quiet --exists-action i 2>nul

echo.
echo  Lancement du screener...
echo  Duree estimee : 5 a 10 minutes
echo.

cd /d "%~dp0"
python stock_screener_v3.py

if exist "daily_report.html" (
    echo.
    echo  Rapport genere avec succes !
    echo  Ouverture dans le navigateur...
    start "" "daily_report.html"
) else (
    echo.
    echo  ERREUR : Le rapport n'a pas ete genere.
    echo  Verifiez votre connexion internet.
)

echo.
pause
