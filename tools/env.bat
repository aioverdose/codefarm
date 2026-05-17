@echo off
rem CodeFarm local environment. Keep all project paths rooted under G:\codefarm.
set "CODEFARM_ROOT=G:\codefarm"
set "CODEFARM_TOOLS=%CODEFARM_ROOT%\tools"
set "CODEFARM_LOGS=%CODEFARM_ROOT%\logs"
set "CODEFARM_STATE=%CODEFARM_ROOT%\state.json"
set "TERRAFORM_CONFIG=%CODEFARM_ROOT%\tools\terraform.rc"
set "TF_DATA_DIR=%CODEFARM_ROOT%\.terraform"
set "ANSIBLE_HOME=%CODEFARM_ROOT%\tools\ansible"
set "PIP_CACHE_DIR=%CODEFARM_ROOT%\tools\pip-cache"
set "PYTHONPYCACHEPREFIX=%CODEFARM_ROOT%\tools\pycache"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "LANG=C.UTF-8"
set "LC_ALL=C.UTF-8"
set "TEMP=%CODEFARM_ROOT%\tools\tmp"
set "TMP=%CODEFARM_ROOT%\tools\tmp"

if not exist "%CODEFARM_TOOLS%\tmp" mkdir "%CODEFARM_TOOLS%\tmp"
if not exist "%CODEFARM_TOOLS%\pip-cache" mkdir "%CODEFARM_TOOLS%\pip-cache"
if not exist "%CODEFARM_TOOLS%\terraform.d" mkdir "%CODEFARM_TOOLS%\terraform.d"
if not exist "%CODEFARM_TOOLS%\pycache" mkdir "%CODEFARM_TOOLS%\pycache"

if exist "%CODEFARM_TOOLS%\python\python.exe" (
  set "PYTHON_EXE=%CODEFARM_TOOLS%\python\python.exe"
) else (
  set "PYTHON_EXE=python"
)

set "PATH=%CODEFARM_TOOLS%\bin;%CODEFARM_TOOLS%\python-venv\Scripts;%CODEFARM_TOOLS%\python;%CODEFARM_TOOLS%\python\Scripts;%CODEFARM_TOOLS%\terraform;%PATH%"

echo G CODEFARM environment loaded.
echo Root: %CODEFARM_ROOT%
echo Python: %PYTHON_EXE%





