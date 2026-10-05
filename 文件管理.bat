@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
set PY=C:\Users\Floyd\.workbuddy\binaries\python\versions\3.13.12\python.exe

:menu
cls
echo ============================================================
echo   SITE FILE MANAGER   -   yuanshu-anime-archive
echo ============================================================
echo.
echo   [1] Delete a FOLDER
echo   [2] Delete a FILE
echo   [3] Rebuild and repackage site
echo   [4] Push to GitHub
echo   [5] List committed files
echo   [0] Quit
echo ------------------------------------------------------------
echo.
set /p C=Enter number:

if "%C%"=="0" exit
if "%C%"=="1" goto deldir
if "%C%"=="2" goto delfile
if "%C%"=="3" goto repack
if "%C%"=="4" goto push
if "%C%"=="5" goto list
goto menu

:deldir
echo.
set /p D=Folder path to delete (e.g. site/covers):
if "%D%"=="" goto menu
echo.
echo About to delete folder: %D%
choice /C YN /N /M "Confirm? (Y/N): "
if errorlevel 2 goto menu
if exist "%D%" (
    rmdir /S /Q "%D%"
    git add -A
    git commit -m "delete %D%" 2>nul
    echo DELETED and committed. Now use [4] to push.
) else (
    echo NOT FOUND: %D%
)
goto menu

:delfile
echo.
set /p F=File path to delete:
if "%F%"=="" goto menu
echo.
echo About to delete file: %F%
choice /C YN /N /M "Confirm? (Y/N): "
if errorlevel 2 goto menu
if exist "%F%" (
    del /Q "%F%"
    git add -A
    git commit -m "delete %F%" 2>nul
    echo DELETED and committed. Now use [4] to push.
) else (
    echo NOT FOUND: %F%
)
goto menu

:repack
echo.
echo Rebuilding page and packaging...
echo.
"%PY%" build_page.py
"%PY%" package_site.py
echo.
git add -A
git commit -m "update site" 2>nul
echo.
echo DONE. Now use [4] to push.
goto menu

:push
echo.
set /p R=Paste your GitHub repo URL (https://github.com/xxx/xxx.git):
if "%R%"=="" goto menu
git branch -M main
git remote remove origin 2>nul
git remote add origin %R%
echo.
echo Pushing (740 covers, first time takes 1-3 min)...
git push -u origin main
echo.
echo If it asks for login, use a Personal Access Token as password.
echo Generate one at: https://github.com/settings/tokens  (check "repo")
pause
goto menu

:list
echo.
git ls-files
echo.
pause
goto menu
