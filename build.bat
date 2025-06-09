@echo off
REM Terry-Form MCP Build Script for Windows
REM Builds Docker image and runs basic tests

echo Building Terry-Form MCP Docker Image
echo ===========================================

set IMAGE_NAME=terry-form-mcp

echo Building image: %IMAGE_NAME%
docker build -t %IMAGE_NAME% .

if %ERRORLEVEL% NEQ 0 (
    echo Docker build failed!
    exit /b 1
)

echo Docker build successful!

echo.
echo Running Tests
echo ==============

echo Test 1: Basic JSON input processing
echo {"actions":["validate"],"path":"test"} | docker run -i --rm %IMAGE_NAME% python3 terry-form-mcp.py 2>nul
echo Basic test completed

echo.
echo Test 2: FastMCP server startup
timeout /t 5 /nobreak >nul
docker run --rm %IMAGE_NAME% >nul 2>&1
echo Server startup test completed

echo.
echo Test 3: Sample test.json processing
docker run -i --rm -v "%cd%:/mnt/workspace" %IMAGE_NAME% python3 terry-form-mcp.py < test.json
echo Sample test completed

echo.
echo All tests completed!
echo Image ready: %IMAGE_NAME%

echo.
echo Usage Instructions
echo ==================
echo Run as MCP Server:
echo docker run -it --rm -v "%cd%:/mnt/workspace" %IMAGE_NAME%
echo.
echo Test with sample data:
echo docker run -i --rm -v "%cd%:/mnt/workspace" %IMAGE_NAME% python3 terry-form-mcp.py ^< test.json