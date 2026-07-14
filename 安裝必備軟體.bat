@echo off
setlocal EnableExtensions
title MediaManager One-click Dependency Installer

echo ============================================================
echo MediaManager - One-click Dependency Installer
echo ============================================================
echo This tool detects and installs missing FFmpeg, ffprobe and Deno.
echo Bundled Portable tools and existing system installations are skipped.
echo Packages are installed through Windows Package Manager (winget).
echo A license agreement or Windows UAC prompt may appear.
echo.

set "FAILED=0"
set "NEED_WINGET=0"

call :detect ffmpeg "%~dp0tools\ffmpeg.exe" "FFmpeg"
if errorlevel 1 set "NEED_WINGET=1"
call :detect ffprobe "%~dp0tools\ffprobe.exe" "ffprobe"
if errorlevel 1 set "NEED_WINGET=1"
call :detect deno "%~dp0tools\deno.exe" "Deno / yt-dlp EJS runtime"
if errorlevel 1 set "NEED_WINGET=1"

if "%NEED_WINGET%"=="0" goto complete

where winget >nul 2>&1
if errorlevel 1 (
    echo [CANNOT INSTALL] Windows Package Manager ^(winget^) was not found.
    echo Update "App Installer" in Microsoft Store, then run this file again.
    set "FAILED=1"
    goto complete
)

call :install_media_if_missing
call :install_if_missing deno "%~dp0tools\deno.exe" DenoLand.Deno "Deno / yt-dlp EJS runtime"

:complete
echo.
if "%FAILED%"=="0" (
    echo [DONE] Required external software is available.
    echo Restart MediaManager so that its environment check is refreshed.
) else (
    echo [INCOMPLETE] An installation failed or was cancelled.
    echo Review the winget message above and run this file again after fixing it.
)
echo.
echo NOTE: Speech to Text is optional and also needs whisper-cli plus a local model.
echo It is not required to start MediaManager, so models are not installed here.
pause
exit /b %FAILED%

:detect
where %~1 >nul 2>&1
if not errorlevel 1 (
    echo [AVAILABLE] %~3
    exit /b 0
)
if exist "%~2" (
    echo [BUNDLED] %~3
    exit /b 0
)
echo [MISSING] %~3
exit /b 1

:install_if_missing
where %~1 >nul 2>&1
if not errorlevel 1 exit /b 0
if exist "%~2" exit /b 0
echo.
echo [INSTALLING] %~4
winget install --id "%~3" --exact --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo [FAILED] %~4
    set "FAILED=1"
) else (
    echo [INSTALLED] %~4
)
exit /b 0

:install_media_if_missing
where ffmpeg >nul 2>&1
if errorlevel 1 goto install_media
where ffprobe >nul 2>&1
if errorlevel 1 goto install_media
exit /b 0

:install_media
if exist "%~dp0tools\ffmpeg.exe" if exist "%~dp0tools\ffprobe.exe" exit /b 0
echo.
echo [INSTALLING] FFmpeg / ffprobe
winget install --id "Gyan.FFmpeg" --exact --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo [FAILED] FFmpeg / ffprobe
    set "FAILED=1"
) else (
    echo [INSTALLED] FFmpeg / ffprobe
)
exit /b 0
