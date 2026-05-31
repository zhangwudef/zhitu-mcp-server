@echo off
title MCP Server

cd /d "%~dp0"

set "PY=D:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.169\runtime\python311\python.exe"

if not exist "%PY%" (
    echo Python not found: %PY%
    pause
    exit /b 1
)

echo Starting MCP Server on port 8090...
echo.
echo   SSE endpoint: http://localhost:8090/sse
echo.
echo ============================================

"%PY%" server.py --port 8090

pause
