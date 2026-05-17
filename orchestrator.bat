@echo off
setlocal EnableExtensions

set "CODEFARM_ROOT=G:\codefarm"
if exist "%CODEFARM_ROOT%\tools\env.bat" call "%CODEFARM_ROOT%\tools\env.bat"

if "%~1"=="" goto help
if /I "%~1"=="bootstrap" goto overmind
if /I "%~1"=="genesis" goto overmind
if /I "%~1"=="cycle" goto overmind
if /I "%~1"=="status" goto overmind
if /I "%~1"=="continuous" goto continuous
if /I "%~1"=="agent-genesis" goto agent_genesis
if /I "%~1"=="digest" goto digest
if /I "%~1"=="metrics" goto metrics
if /I "%~1"=="help" goto help

echo Unknown command: %~1
echo.
goto help

:overmind
"%PYTHON_EXE%" "%CODEFARM_ROOT%\overmind.py" %~1
goto end

:continuous
set "DELAY_SECONDS=%~2"
set "MAX_CYCLES=%~3"
if "%DELAY_SECONDS%"=="" set "DELAY_SECONDS=60"
set /A CYCLE_COUNT=0

echo G CODEFARM continuous mode started.
echo Delay seconds: %DELAY_SECONDS%
if "%MAX_CYCLES%"=="" (
  echo Max cycles: unlimited
) else (
  echo Max cycles: %MAX_CYCLES%
)
echo Press Ctrl+C to stop.
echo.

:continuous_loop
set /A CYCLE_COUNT+=1
echo G CODEFARM continuous cycle %CYCLE_COUNT% starting...
"%PYTHON_EXE%" "%CODEFARM_ROOT%\overmind.py" cycle
if errorlevel 1 goto continuous_fail
if not "%MAX_CYCLES%"=="" if %CYCLE_COUNT% GEQ %MAX_CYCLES% goto continuous_done
timeout /t %DELAY_SECONDS% /nobreak >nul
goto continuous_loop

:continuous_fail
echo G CODEFARM continuous mode stopped after a cycle failure.
goto end

:continuous_done
echo G CODEFARM continuous mode completed %CYCLE_COUNT% cycle(s).
goto end

:agent_genesis
"%PYTHON_EXE%" "%CODEFARM_ROOT%\agent_orchestrator.py"
goto end

:digest
if "%~2"=="" goto digest_help
if "%~3"=="" goto digest_help
"%PYTHON_EXE%" "%CODEFARM_ROOT%\digestive-engine\digest.py" %~2 %~3
goto end

:agent_genesis
"%PYTHON_EXE%" "%CODEFARM_ROOT%\agent_orchestrator.py"
goto end

:digest_help
echo Usage: %~nx0 digest ORGANISM_ID OUTPUT_FILE
echo Example: %~nx0 digest test-org G:\codefarm\organisms\test-org\output\test.py
goto end

:metrics
"%PYTHON_EXE%" "%CODEFARM_ROOT%\observatory\metrics-collector.py"
goto end

:help
echo G CODEFARM orchestrator
echo.
echo Usage:
echo   %~nx0 bootstrap
echo   %~nx0 genesis
echo   %~nx0 cycle
echo   %~nx0 continuous [delay_seconds] [max_cycles]
echo   %~nx0 agent-genesis
echo   %~nx0 status
echo   %~nx0 metrics
echo   %~nx0 digest ORGANISM_ID OUTPUT_FILE
echo.
echo Examples:
echo   %~nx0 continuous
echo   %~nx0 continuous 60
echo   %~nx0 continuous 5 3
echo.
echo Root: %CODEFARM_ROOT%

:end
endlocal

