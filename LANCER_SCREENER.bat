@echo off
title Market Screener v3
chcp 65001 >nul 2>&1

echo.
echo  =========================================
echo   MARKET SCREENER v3
echo   CAC40 - DAX - AEX - IBEX - FTSE
echo   SP500 - NASDAQ100 - US Growth
echo  =========================================
echo.

cd /d "%~dp0"

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
echo  Duree estimee : 10 a 15 minutes
echo.

python stock_screener_v3.py

echo.
if exist "daily_report.html" (
    echo  =========================================
    echo   Rapport genere avec succes !
    echo  =========================================
    echo.
    start "" "daily_report.html"
) else (
    echo  ERREUR : Rapport non genere.
    echo  Verifiez votre connexion internet.
)

echo.
pause
