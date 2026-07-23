@echo off
setlocal EnableExtensions
title MediaManager Temporary File Cleanup

REM This script only cleans generated files under the folder that contains it.
REM Optional: run with /quiet to skip the final pause.

set "ROOT=%~dp0"
set /a CLEANED=0
set /a FAILED=0

echo ============================================================
echo MediaManager - Project Temporary File Cleanup
echo ============================================================
echo Project root: %ROOT%
echo.

if not exist "%ROOT%pyproject.toml" (
    echo [STOP] pyproject.toml was not found beside this script.
    echo Move this BAT file back to the MediaManager project root.
    set "FAILED=1"
    goto summary
)

set "APP_RUNNING=0"
for /f "tokens=1 delims=," %%P in ('%SystemRoot%\System32\tasklist.exe /FI "IMAGENAME eq MediaManager.exe" /FO CSV /NH 2^>nul') do (
    if /I "%%~P"=="MediaManager.exe" set "APP_RUNNING=1"
)
if "%APP_RUNNING%"=="1" (
    echo [STOP] MediaManager.exe is still running.
    echo Close MediaManager and run this file again.
    set "FAILED=1"
    goto summary
)

echo [KEEP] %ROOT%.work (may contain backups, build receipts, worktrees and validation evidence)
call :remove_dir "%ROOT%.pytest_cache" ".pytest_cache"
call :remove_dir "%ROOT%.pytest-agent-domain" ".pytest-agent-domain"
call :remove_dir "%ROOT%pytest-temp-social" "pytest-temp-social"
call :remove_dir "%ROOT%.ruff_cache" ".ruff_cache"
call :remove_dir "%ROOT%.mypy_cache" ".mypy_cache"
call :remove_dir "%ROOT%.hypothesis" ".hypothesis"
call :remove_dir "%ROOT%build" "build"
call :clean_dist "%ROOT%dist"
call :remove_dir "%ROOT%dist-packages" "dist-packages"
call :remove_dir "%ROOT%mediamanager.egg-info" "mediamanager.egg-info"
call :remove_dir "%ROOT%htmlcov" "htmlcov"
call :remove_dir "%ROOT%pytest-of-%USERNAME%" "project-local pytest temporary folder"

call :remove_file "%ROOT%.sandbox-test" ".sandbox-test"
call :remove_file "%ROOT%.coverage" ".coverage"
call :remove_file "%ROOT%coverage.xml" "coverage.xml"

call :remove_dir "%ROOT%__pycache__" "root __pycache__"
call :clean_tree "%ROOT%contracts"
call :clean_tree "%ROOT%core"
call :clean_tree "%ROOT%plugin_host"
call :clean_tree "%ROOT%trusted_ui"
call :clean_tree "%ROOT%tools"
call :clean_tree "%ROOT%tests"
call :clean_tree "%ROOT%mod\builtin"

echo.
echo [KEEP] Version, .venv, .tool-cache and all user/download data were preserved.
echo [KEEP] System TEMP and files outside this project were not touched.

:summary
echo.
echo Cleaned items: %CLEANED%
if "%FAILED%"=="0" (
    echo [DONE] Project temporary files are clean.
) else (
    echo [INCOMPLETE] One or more items could not be cleaned.
    echo Close programs using this project, restart Windows if needed, and retry.
)
echo.
if /I not "%~1"=="/quiet" pause
exit /b %FAILED%

:clean_dist
if not exist "%~1" exit /b 0
echo [CLEAN] dist build output
for /d %%D in ("%~1\*") do (
    if /I "%%~nxD"=="UserData" (
        echo [KEEP] %%~fD
    ) else (
        call :remove_dir "%%~fD" "dist generated directory"
    )
)
for %%F in ("%~1\*") do (
    if exist "%%~fF" call :remove_file "%%~fF" "dist generated file"
)
if exist "%~1\UserData" exit /b 0
call :remove_dir "%~1" "dist"
exit /b 0

:clean_tree
if not exist "%~1" exit /b 0
for /d /r "%~1" %%D in (__pycache__) do call :remove_dir "%%~fD" "__pycache__"
for /r "%~1" %%F in (*.pyc *.pyo) do call :remove_file "%%~fF" "Python bytecode"
exit /b 0

:remove_dir
if not exist "%~1" exit /b 0
echo [REMOVE] %~2
rmdir /s /q "%~1" 2>nul
if exist "%~1" (
    echo [FAILED] %~1
    set /a FAILED+=1
) else (
    set /a CLEANED+=1
)
exit /b 0

:remove_file
if not exist "%~1" exit /b 0
echo [REMOVE] %~2
del /f /q "%~1" 2>nul
if exist "%~1" (
    echo [FAILED] %~1
    set /a FAILED+=1
) else (
    set /a CLEANED+=1
)
exit /b 0
