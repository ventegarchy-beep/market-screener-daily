@echo off
title Stock Screener v3 - VERSION PUBLIC

echo.
echo =========================================
echo MARKET SCREENER v3 - VERSION PUBLIC
echo S&P500 - NASDAQ100 - CAC40
echo =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR : Python n'est pas installe.
    echo Telechargez-le sur https://www.python.org
    pause
    exit /b
)

echo Installation des dependances...
pip install yfinance pandas numpy requests lxml --quiet --exists-action i 2>nul

echo.
echo Lancement du screener PUBLIC...
echo Duree estimee : 5 a 10 minutes
echo.

cd /d "%~dp0"
python stock_screener_v3.py

if exist "daily_report.html" (
    echo.
    echo ✓ Rapport PUBLIC genere avec succes !
    echo Fichier : daily_report.html
    echo Pret a partager (GitHub, email...)
    echo.
    echo Ouverture automatique...
    start "" "daily_report.html"
) else (
    echo.
    echo ERREUR : daily_report.html non genere.
    echo Verifiez votre connexion internet.
)

echo.
pause
