@echo off
title Publication GitHub
chcp 65001 >nul 2>&1

REM ============================================================
REM  CONFIGURATION — A remplir une seule fois
REM ============================================================
set GITHUB_USER=ventegarchy-beep
set GITHUB_REPO=market-screener-daily
set GITHUB_EMAIL=ton@email.com
set GITHUB_NAME=ventegarchy
REM ============================================================

cd /d "%~dp0"

git --version >nul 2>&1
if errorlevel 1 ( echo Git non installe - https://git-scm.com & pause & exit /b )

if not exist "daily_report.html" ( echo daily_report.html introuvable & pause & exit /b )

if not exist ".git" (
    echo  Initialisation...
    git init
    git config user.email "%GITHUB_EMAIL%"
    git config user.name "%GITHUB_NAME%"
    echo # Market Screener — Rapports Journaliers > README.md
    echo. >> README.md
    echo [Voir le dernier rapport](https://htmlpreview.github.io/?https://github.com/%GITHUB_USER%/%GITHUB_REPO%/blob/main/daily_report.html) >> README.md
    echo. >> README.md
    echo *Analyse CAC40 - DAX - AEX - IBEX - FTSE MIB - FTSE100 - SP500 - NASDAQ100 - Growth US* >> README.md
    echo *.py > .gitignore
    echo *.bat >> .gitignore
    echo watchlist.txt >> .gitignore
    echo __pycache__/ >> .gitignore
    git add .gitignore README.md daily_report.html
    git commit -m "Init"
    git branch -M main
    git remote add origin https://github.com/%GITHUB_USER%/%GITHUB_REPO%.git
    echo.
    echo  Creez le repo GitHub avant de continuer :
    echo  1. https://github.com/new
    echo  2. Nom : %GITHUB_REPO%
    echo  3. Visibilite : PUBLIC
    echo  4. NE PAS cocher Add README
    echo  5. Relancez ce fichier
    pause & exit /b
)

git config user.email "%GITHUB_EMAIL%"
git config user.name "%GITHUB_NAME%"
git remote set-url origin https://github.com/%GITHUB_USER%/%GITHUB_REPO%.git

set DH=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%_%TIME:~0,2%h%TIME:~3,2%
git add daily_report.html README.md
git commit -m "Rapport %DH%"
git push -u origin main

if errorlevel 1 (
    echo.
    echo  Echec. Mot de passe = Personal Access Token
    echo  Creer ici : https://github.com/settings/tokens (cocher repo)
    pause & exit /b
)

echo.
echo  =========================================
echo   PUBLIE !
echo  =========================================
echo.
echo  Lien permanent :
echo  https://htmlpreview.github.io/?https://github.com/%GITHUB_USER%/%GITHUB_REPO%/blob/main/daily_report.html
echo.
echo https://htmlpreview.github.io/?https://github.com/%GITHUB_USER%/%GITHUB_REPO%/blob/main/daily_report.html | clip
echo  (Copie dans le presse-papier)
echo.
pause
