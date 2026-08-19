@echo off
setlocal EnableExtensions

set "ROOT=%~dp0.."
pushd "%ROOT%"

where py >nul 2>nul
if not errorlevel 1 (
    if "%~1"=="" (
        py -3 tools\build_openapi.py --build-only
    ) else (
        py -3 tools\build_openapi.py --build-only --source-root "%~1"
    )
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 was not found.
        popd
        pause
        exit /b 1
    )
    if "%~1"=="" (
        python tools\build_openapi.py --build-only
    ) else (
        python tools\build_openapi.py --build-only --source-root "%~1"
    )
)

if errorlevel 1 (
    echo OpenAPI build failed. Nothing was pushed.
    popd
    pause
    exit /b 1
)

git add openapi
git diff --cached --quiet
if not errorlevel 1 (
    git commit -m "docs: update OpenAPI documents"
    if errorlevel 1 (
        echo Commit failed. Nothing was pushed.
        popd
        pause
        exit /b 1
    )
    git push origin main
) else (
    echo No OpenAPI document changes to publish.
)

popd
pause
